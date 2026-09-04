from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .production_data import require_publishable_manifest
from .report_contract import validate_report_payload
from .ticker_symbol import is_valid_hose_ticker


HORIZONS = frozenset({"SHORT_TERM", "MEDIUM_TERM", "LONG_TERM", "ACCUMULATION"})
SENSITIVE_KEY_FRAGMENTS = (
    "api_key",
    "apikey",
    "secret",
    "password",
    "authorization",
    "access_token",
    "refresh_token",
    "service_role",
    "trading_token",
    "otp",
)


class CachePublishError(ValueError):
    pass


@dataclass(frozen=True)
class CacheRecord:
    ticker: str
    horizon: str
    snapshot_id: str
    generated_at: str
    expires_at: str
    payload: dict[str, Any]
    source_manifest_ref: str

    def rpc_payload(self) -> dict[str, Any]:
        return {
            "p_ticker": self.ticker,
            "p_horizon": self.horizon,
            "p_snapshot_id": self.snapshot_id,
            "p_generated_at": self.generated_at,
            "p_expires_at": self.expires_at,
            "p_payload": self.payload,
            "p_source_manifest_ref": self.source_manifest_ref,
        }


def _parse_timestamp(value: object, field_name: str) -> datetime:
    text = str(value or "").strip()
    if not text:
        raise CachePublishError(f"{field_name} is required")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        raise CachePublishError(f"{field_name} must be ISO-8601") from error
    if parsed.tzinfo is None:
        raise CachePublishError(f"{field_name} must include a timezone")
    return parsed


def _normalize_ticker(value: object) -> str:
    ticker = str(value or "").strip().upper()
    if not is_valid_hose_ticker(ticker):
        raise CachePublishError(f"invalid ticker: {ticker!r}")
    return ticker


def _normalize_horizon(value: object) -> str:
    horizon = str(value or "").strip().upper()
    if horizon not in HORIZONS:
        raise CachePublishError(f"invalid horizon: {horizon!r}")
    return horizon


def _sensitive_paths(value: object, path: tuple[str, ...] = ()) -> list[str]:
    findings: list[str] = []
    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            key = str(raw_key)
            normalized = key.lower().replace("-", "_")
            child_path = (*path, key)
            if any(fragment in normalized for fragment in SENSITIVE_KEY_FRAGMENTS):
                findings.append(".".join(child_path))
            findings.extend(_sensitive_paths(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_sensitive_paths(child, (*path, str(index))))
    return findings


def _manifest_ref(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"sha256:{digest}"


def load_cache_batch(
    manifest_path: str | Path,
    batch_path: str | Path,
    *,
    now: datetime | None = None,
    max_age_seconds: int = 21_600,
) -> tuple[str, list[CacheRecord]]:
    manifest_file = Path(manifest_path)
    batch_file = Path(batch_path)
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise CachePublishError("now must include a timezone")

    gate = require_publishable_manifest(
        manifest_file,
        now=current,
        max_age_seconds=max_age_seconds,
    )
    manifest_reference = _manifest_ref(manifest_file)

    payload = json.loads(batch_file.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise CachePublishError("cache batch must be a JSON object")
    if str(payload.get("contract_version") or "").strip() != "1.0":
        raise CachePublishError("cache batch contract_version must be '1.0'")
    snapshot_id = str(payload.get("snapshot_id") or "").strip()
    if not snapshot_id or snapshot_id != gate.snapshot_id:
        raise CachePublishError("cache batch snapshot does not match production manifest")

    manifest_payload = json.loads(manifest_file.read_text(encoding="utf-8"))
    snapshot_payload = manifest_payload.get("snapshot") if isinstance(manifest_payload, Mapping) else None
    if not isinstance(snapshot_payload, Mapping):
        raise CachePublishError("production manifest snapshot is missing")
    snapshot_as_of = _parse_timestamp(snapshot_payload.get("as_of"), "manifest snapshot.as_of")

    raw_items = payload.get("items")
    if not isinstance(raw_items, list) or not raw_items:
        raise CachePublishError("cache batch items must be a non-empty list")

    records: list[CacheRecord] = []
    seen: set[tuple[str, str]] = set()
    for index, raw_item in enumerate(raw_items):
        if not isinstance(raw_item, Mapping):
            raise CachePublishError(f"cache item {index} must be an object")
        ticker = _normalize_ticker(raw_item.get("ticker"))
        horizon = _normalize_horizon(raw_item.get("horizon"))
        identity = (ticker, horizon)
        if identity in seen:
            raise CachePublishError(f"duplicate cache item: {ticker}/{horizon}")
        seen.add(identity)

        generated_at = _parse_timestamp(raw_item.get("generated_at"), f"item {index} generated_at")
        expires_at = _parse_timestamp(raw_item.get("expires_at"), f"item {index} expires_at")
        if generated_at < snapshot_as_of:
            raise CachePublishError(f"item {index} generated_at predates manifest snapshot")
        if expires_at <= generated_at:
            raise CachePublishError(f"item {index} expires_at must be after generated_at")
        if generated_at > current.astimezone(generated_at.tzinfo) and (
            generated_at - current.astimezone(generated_at.tzinfo)
        ).total_seconds() > 300:
            raise CachePublishError(f"item {index} generated_at is too far in the future")

        report_payload = raw_item.get("payload")
        if not isinstance(report_payload, Mapping):
            raise CachePublishError(f"item {index} payload must be an object")
        report_object = dict(report_payload)
        sensitive = _sensitive_paths(report_object)
        if sensitive:
            raise CachePublishError(
                f"item {index} contains forbidden secret-shaped field: {sensitive[0]}"
            )
        report_object = validate_report_payload(
            report_object,
            expected_ticker=ticker,
            expected_horizon=horizon,
        )

        records.append(
            CacheRecord(
                ticker=ticker,
                horizon=horizon,
                snapshot_id=snapshot_id,
                generated_at=generated_at.isoformat(),
                expires_at=expires_at.isoformat(),
                payload=report_object,
                source_manifest_ref=manifest_reference,
            )
        )

    return manifest_reference, records


def publish_cache_records(
    records: list[CacheRecord],
    *,
    supabase_url: str | None = None,
    service_role_key: str | None = None,
    timeout_seconds: int = 20,
) -> int:
    url = (supabase_url or os.environ.get("SUPABASE_URL") or "").strip().rstrip("/")
    key = (service_role_key or os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    if not url.startswith("https://"):
        raise CachePublishError("SUPABASE_URL must be an HTTPS URL")
    if not key:
        raise CachePublishError("SUPABASE_SERVICE_ROLE_KEY is required in the environment")
    if timeout_seconds <= 0:
        raise CachePublishError("timeout_seconds must be positive")

    endpoint = f"{url}/rest/v1/rpc/upsert_stockradar_cached_report"
    published = 0
    for record in records:
        body = json.dumps(record.rpc_payload(), ensure_ascii=False).encode("utf-8")
        request = Request(
            endpoint,
            data=body,
            method="POST",
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                if response.status not in (200, 204):
                    raise CachePublishError(
                        f"cache publish failed with HTTP {response.status} for {record.ticker}/{record.horizon}"
                    )
        except HTTPError as error:
            raise CachePublishError(
                f"cache publish failed with HTTP {error.code} for {record.ticker}/{record.horizon}"
            ) from error
        except URLError as error:
            raise CachePublishError(
                f"cache publish connection failed for {record.ticker}/{record.horizon}"
            ) from error
        published += 1
    return published
