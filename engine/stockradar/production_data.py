from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping

from .models import UniverseSnapshot
from .ranking import full_universe_gate


CONTRACT_VERSION = "1.0"
REQUIRED_DATASETS = (
    "security_master",
    "ohlcv",
    "fundamentals",
    "corporate_actions",
    "events",
)
COVERAGE_DATASETS = {"security_master", "ohlcv", "fundamentals"}
SENSITIVE_KEY_FRAGMENTS = (
    "api_key",
    "apikey",
    "secret",
    "password",
    "authorization",
    "access_token",
    "refresh_token",
    "trading_token",
    "otp",
)


@dataclass(frozen=True)
class ProductionDataGateResult:
    passed: bool
    failures: tuple[str, ...]
    warnings: tuple[str, ...]
    snapshot_id: str | None
    as_of: str | None
    coverage_pct: float
    required_datasets: tuple[str, ...] = REQUIRED_DATASETS

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "publication_allowed": self.passed,
            "ranking_allowed": self.passed,
            "failures": list(self.failures),
            "warnings": list(self.warnings),
            "snapshot_id": self.snapshot_id,
            "as_of": self.as_of,
            "coverage_pct": self.coverage_pct,
            "required_datasets": list(self.required_datasets),
            "contract_version": CONTRACT_VERSION,
        }


class ProductionDataGateError(RuntimeError):
    pass


def _parse_timestamp(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed


def _checksum_valid(value: object) -> bool:
    text = str(value or "").strip().lower()
    return len(text) == 64 and all(character in "0123456789abcdef" for character in text)


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


def _dedupe(values: list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def validate_production_manifest(
    payload: Mapping[str, Any],
    *,
    now: datetime | None = None,
    max_age_seconds: int = 21_600,
    future_tolerance_seconds: int = 300,
) -> ProductionDataGateResult:
    failures: list[str] = []
    warnings: list[str] = []
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    if max_age_seconds <= 0:
        raise ValueError("max_age_seconds must be positive")
    if future_tolerance_seconds < 0:
        raise ValueError("future_tolerance_seconds must be non-negative")

    if str(payload.get("contract_version", "")).strip() != CONTRACT_VERSION:
        failures.append("contract_version_unsupported")

    for path in _sensitive_paths(payload):
        failures.append(f"secret_material_forbidden:{path}")

    raw_snapshot = payload.get("snapshot")
    snapshot: UniverseSnapshot | None = None
    if not isinstance(raw_snapshot, Mapping):
        failures.append("snapshot_missing")
    else:
        try:
            snapshot = UniverseSnapshot.from_dict(dict(raw_snapshot))
        except (KeyError, TypeError, ValueError):
            failures.append("snapshot_invalid")

    snapshot_as_of: datetime | None = None
    if snapshot is not None:
        failures.extend(full_universe_gate(snapshot).failures)
        snapshot_as_of = _parse_timestamp(snapshot.as_of)
        source_timestamp = _parse_timestamp(snapshot.source_timestamp)
        if snapshot_as_of is None or source_timestamp is None:
            failures.append("snapshot_timestamp_invalid")
        else:
            age = (current.astimezone(timezone.utc) - snapshot_as_of.astimezone(timezone.utc)).total_seconds()
            if age > max_age_seconds:
                failures.append("snapshot_stale")
            if age < -future_tolerance_seconds:
                failures.append("snapshot_from_future")
            source_age = (
                current.astimezone(timezone.utc) - source_timestamp.astimezone(timezone.utc)
            ).total_seconds()
            if source_age > max_age_seconds:
                failures.append("source_timestamp_stale")
            if source_age < -future_tolerance_seconds:
                failures.append("source_timestamp_from_future")

    rights = payload.get("rights")
    if not isinstance(rights, Mapping):
        failures.append("rights_evidence_missing")
    else:
        for key in ("publication_allowed", "redistribution_allowed", "source_terms_reviewed"):
            if rights.get(key) is not True:
                failures.append(f"rights_{key}_false")
        if not str(rights.get("evidence_ref", "")).strip():
            failures.append("rights_evidence_ref_missing")

    active_status = payload.get("active_status")
    if not isinstance(active_status, Mapping):
        failures.append("active_status_evidence_missing")
    else:
        if active_status.get("semantics_resolved") is not True:
            failures.append("active_status_semantics_unresolved")
        if active_status.get("market_status_checked") is not True:
            failures.append("market_status_not_checked")

    datasets = payload.get("datasets")
    if not isinstance(datasets, Mapping):
        failures.append("datasets_missing")
        datasets = {}

    for name in REQUIRED_DATASETS:
        raw_dataset = datasets.get(name)
        if not isinstance(raw_dataset, Mapping) or raw_dataset.get("present") is not True:
            failures.append(f"dataset_missing:{name}")
            continue

        dataset_snapshot_id = str(raw_dataset.get("snapshot_id", "")).strip()
        if snapshot is not None and dataset_snapshot_id != snapshot.snapshot_id:
            failures.append(f"dataset_snapshot_mismatch:{name}")

        if not _checksum_valid(raw_dataset.get("sha256")):
            failures.append(f"dataset_checksum_invalid:{name}")

        try:
            row_count = int(raw_dataset.get("row_count"))
        except (TypeError, ValueError):
            row_count = -1
        if row_count < 0:
            failures.append(f"dataset_row_count_invalid:{name}")
        elif name in COVERAGE_DATASETS and row_count == 0:
            failures.append(f"dataset_empty:{name}")

        dataset_as_of = _parse_timestamp(raw_dataset.get("as_of"))
        if dataset_as_of is None:
            failures.append(f"dataset_timestamp_invalid:{name}")
        else:
            age = (current.astimezone(timezone.utc) - dataset_as_of.astimezone(timezone.utc)).total_seconds()
            if age > max_age_seconds:
                failures.append(f"dataset_stale:{name}")
            if age < -future_tolerance_seconds:
                failures.append(f"dataset_from_future:{name}")

        if name in COVERAGE_DATASETS and snapshot is not None:
            try:
                covered_tickers = int(raw_dataset.get("covered_tickers"))
            except (TypeError, ValueError):
                covered_tickers = -1
            required_coverage = (
                snapshot.expected_total if name == "security_master" else snapshot.valid_count
            )
            if covered_tickers < required_coverage:
                failures.append(f"dataset_coverage_incomplete:{name}")

    if snapshot is not None and snapshot.exchange == "HOSE":
        if snapshot.expected_total < 300:
            warnings.append("unexpectedly_small_hose_universe")

    return ProductionDataGateResult(
        passed=not failures,
        failures=_dedupe(failures),
        warnings=_dedupe(warnings),
        snapshot_id=snapshot.snapshot_id if snapshot is not None else None,
        as_of=snapshot.as_of if snapshot is not None else None,
        coverage_pct=snapshot.universe_coverage_pct if snapshot is not None else 0.0,
    )


def load_and_validate_manifest(
    path: str | Path,
    *,
    now: datetime | None = None,
    max_age_seconds: int = 21_600,
    future_tolerance_seconds: int = 300,
) -> ProductionDataGateResult:
    manifest_path = Path(path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("Production manifest must be a JSON object")
    return validate_production_manifest(
        payload,
        now=now,
        max_age_seconds=max_age_seconds,
        future_tolerance_seconds=future_tolerance_seconds,
    )


def require_publishable_manifest(
    path: str | Path,
    *,
    now: datetime | None = None,
    max_age_seconds: int = 21_600,
    future_tolerance_seconds: int = 300,
) -> ProductionDataGateResult:
    result = load_and_validate_manifest(
        path,
        now=now,
        max_age_seconds=max_age_seconds,
        future_tolerance_seconds=future_tolerance_seconds,
    )
    if not result.passed:
        raise ProductionDataGateError(
            "Production Data Gate failed: " + ", ".join(result.failures)
        )
    return result
