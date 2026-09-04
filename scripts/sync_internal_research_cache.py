#!/usr/bin/env python3
"""Sync a private StockRadar ticker lookup bundle into Supabase internal research cache.

This script is intentionally INTERNAL-ONLY. It never opens the public Stock API gate and
it rejects any input row that claims public action/recommendation permission.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from typing import Any
from urllib import error, request

PRIORITY_TICKERS = ("MBB", "HPG", "ACB")
RPC_NAME = "upsert_stockradar_internal_research_context"


class SyncError(RuntimeError):
    pass


def _read_secret_key() -> tuple[str, bool]:
    direct = (os.getenv("SUPABASE_SECRET_KEY") or "").strip()
    if direct:
        return direct, direct.startswith("sb_secret_")

    packed = (os.getenv("SUPABASE_SECRET_KEYS") or "").strip()
    if packed:
        try:
            value = str(json.loads(packed).get("default") or "").strip()
        except json.JSONDecodeError as exc:
            raise SyncError("SUPABASE_SECRET_KEYS is not valid JSON") from exc
        if value:
            return value, True

    legacy = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    if legacy:
        return legacy, False

    raise SyncError("Missing server-only Supabase secret key")


def _load_bundle(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SyncError("Lookup bundle must be UTF-8 JSON") from exc
    if not isinstance(payload, dict):
        raise SyncError("Lookup bundle root must be an object")
    return payload, digest


def _validate_bundle(bundle: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if str(bundle.get("exchange") or "").upper() != "HOSE":
        raise SyncError("Only HOSE bundles are accepted")
    if str(bundle.get("data_role") or "").upper() not in {
        "INTERNAL_BACKEND_RESEARCH",
        "INTERNAL_BACKEND_RESEARCH_POSTCLOSE",
        "INTERNAL_RESEARCH",
    }:
        raise SyncError("Bundle is not marked as internal research")
    if bundle.get("public_release_allowed") is True:
        raise SyncError("Internal sync refuses public-release-enabled bundles")

    tickers = bundle.get("tickers")
    if not isinstance(tickers, dict) or not tickers:
        raise SyncError("Bundle must contain a non-empty tickers object")
    expected = int(bundle.get("universe_count") or 0)
    if expected != len(tickers):
        raise SyncError(f"Universe mismatch: expected {expected}, found {len(tickers)}")

    clean: dict[str, dict[str, Any]] = {}
    for raw_ticker, row in tickers.items():
        ticker = str(raw_ticker or "").strip().upper()
        if len(ticker) != 3 or not ticker.isalnum() or not any(c.isalpha() for c in ticker):
            raise SyncError(f"Invalid HOSE ticker in bundle: {raw_ticker!r}")
        if not isinstance(row, dict):
            raise SyncError(f"Ticker {ticker} payload must be an object")
        release = row.get("release") or {}
        if not isinstance(release, dict):
            raise SyncError(f"Ticker {ticker} release block must be an object")
        if release.get("public_action_allowed") is not False:
            raise SyncError(f"Ticker {ticker} is not explicitly fail-closed for public action")
        if release.get("internal_research_ready") is not True:
            continue
        clean[ticker] = row

    if not clean:
        raise SyncError("No INTERNAL_RESEARCH_READY ticker rows found")
    return clean


def _ordered_tickers(rows: dict[str, dict[str, Any]]) -> list[str]:
    priority = [ticker for ticker in PRIORITY_TICKERS if ticker in rows]
    rest = sorted(ticker for ticker in rows if ticker not in PRIORITY_TICKERS)
    return priority + rest


def _rpc_headers(secret_key: str, is_new_secret_key: bool) -> dict[str, str]:
    headers = {
        "apikey": secret_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "stockradar-internal-research-sync/1.0",
    }
    # New sb_secret_* keys belong on apikey only. Legacy service_role JWTs keep the
    # historical Authorization header until the project finishes key migration.
    if not is_new_secret_key:
        headers["Authorization"] = f"Bearer {secret_key}"
    return headers


def _post_rpc(url: str, headers: dict[str, str], body: dict[str, Any], retries: int = 3) -> None:
    encoded = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    endpoint = f"{url.rstrip('/')}/rest/v1/rpc/{RPC_NAME}"
    for attempt in range(1, retries + 1):
        req = request.Request(endpoint, data=encoded, headers=headers, method="POST")
        try:
            with request.urlopen(req, timeout=30) as resp:
                if 200 <= resp.status < 300:
                    return
                raise SyncError(f"RPC returned HTTP {resp.status}")
        except error.HTTPError as exc:
            if attempt >= retries or exc.code < 500:
                raise SyncError(f"RPC failed with HTTP {exc.code}") from exc
        except error.URLError as exc:
            if attempt >= retries:
                raise SyncError("RPC network failure") from exc
        time.sleep(min(2**attempt, 8))


def sync(path: Path, dry_run: bool = False, limit: int | None = None) -> dict[str, Any]:
    bundle, digest = _load_bundle(path)
    rows = _validate_bundle(bundle)
    ordered = _ordered_tickers(rows)
    if limit is not None:
        ordered = ordered[: max(0, limit)]

    generated_at = str(bundle.get("generated_at_vn") or "").strip()
    as_of_date = str(bundle.get("as_of_date") or "").strip()
    price_status = str(bundle.get("price_snapshot_status") or "").strip()
    if not generated_at or not as_of_date or not price_status:
        raise SyncError("Bundle freshness metadata is incomplete")

    snapshot_id = f"drive-stockradar-{as_of_date.replace('-', '')}-{digest[:16]}"
    source_ref = f"internal-bundle:{path.name}:sha256:{digest}"

    result = {
        "snapshot_id": snapshot_id,
        "source_ref": source_ref,
        "eligible_rows": len(rows),
        "selected_rows": len(ordered),
        "priority_first": ordered[:3],
        "dry_run": dry_run,
    }
    if dry_run:
        return result

    supabase_url = (os.getenv("SUPABASE_URL") or "").strip()
    if not supabase_url:
        raise SyncError("Missing SUPABASE_URL")
    secret_key, is_new_secret_key = _read_secret_key()
    headers = _rpc_headers(secret_key, is_new_secret_key)

    completed = 0
    for ticker in ordered:
        _post_rpc(
            supabase_url,
            headers,
            {
                "p_ticker": ticker,
                "p_snapshot_id": snapshot_id,
                "p_generated_at": generated_at,
                "p_as_of_date": as_of_date,
                "p_price_snapshot_status": price_status,
                "p_payload": rows[ticker],
                "p_source_ref": source_ref,
            },
        )
        completed += 1

    result["synced_rows"] = completed
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync internal StockRadar research cache")
    parser.add_argument("bundle", type=Path, help="Path to stockradar_ticker_lookup_latest.json")
    parser.add_argument("--dry-run", action="store_true", help="Validate only; do not contact Supabase")
    parser.add_argument("--limit", type=int, default=None, help="Optional number of rows to sync")
    args = parser.parse_args()

    try:
        result = sync(args.bundle, dry_run=args.dry_run, limit=args.limit)
    except (OSError, SyncError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
