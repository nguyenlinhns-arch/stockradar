from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = ROOT / "scripts" / "validate_private_scanner_bundle.py"
spec = importlib.util.spec_from_file_location("validate_private_scanner_bundle", VALIDATOR_PATH)
validator = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(validator)


def _tickers() -> list[str]:
    # Synthetic 3-character identifiers; validator contract only requires unique ticker identity here.
    return [f"A{i:02d}" if i < 100 else f"B{i-100:02d}" if i < 200 else f"C{i-200:02d}" if i < 300 else f"D{i-300:02d}" if i < 400 else f"E{i-400:02d}" for i in range(405)]


def _write_bundle(tmp_path: Path, eligible_count: int = 107) -> None:
    tickers = _tickers()
    scanner = pd.DataFrame(
        {
            "ticker": tickers,
            "price": 20.0,
            "vol20": 600_000,
            "stage": "STAGE_2",
            "stockradar_score": 75.0,
            "candidate_setup": "WATCH",
            "rvol_progress_adjusted": 1.2,
            "same_time_volume_ratio": 1.1,
            "pivot20": 20.0,
            "roe_ttm_pct": 15.0,
            "upside_to_base_pct": 20.0,
            "liquidity_pass_500k": True,
            "full_scan_eligible": [i < eligible_count for i in range(405)],
        }
    )
    valuation = pd.DataFrame({"ticker": tickers, "fair_value_base": 24.0})
    website = scanner.iloc[:eligible_count][["ticker", "price", "stockradar_score", "candidate_setup"]].copy()
    website["publication_gate"] = "BLOCKED_PENDING_PRODUCTION_DATA_RIGHTS"

    scanner.to_csv(tmp_path / "stockradar_scanner_master_405_2026-09-04.csv", index=False)
    valuation.to_csv(tmp_path / "stockradar_valuation_bootstrap_405_2026-09-04.csv", index=False)
    website.to_csv(tmp_path / "stockradar_website_feed_internal_2026-09-04.csv", index=False)
    (tmp_path / "stockradar_runtime_manifest_2026-09-04.json").write_text(
        json.dumps({"canonical_universe": 405, "public_feed_allowed": False}), encoding="utf-8"
    )


def test_private_scanner_bundle_accepts_eligible_subset(tmp_path: Path) -> None:
    _write_bundle(tmp_path, eligible_count=107)
    result = validator.validate(tmp_path)
    assert result["status"] == "PASS_INTERNAL"
    assert result["scanner_rows"] == 405
    assert result["eligible_feed_rows"] == 107
    assert result["website_feed_rows"] == 107
    assert result["public_publication_authorized"] is False


def test_private_scanner_bundle_blocks_feed_universe_mismatch(tmp_path: Path) -> None:
    _write_bundle(tmp_path, eligible_count=107)
    feed_path = tmp_path / "stockradar_website_feed_internal_2026-09-04.csv"
    feed = pd.read_csv(feed_path).iloc[:-1]
    feed.to_csv(feed_path, index=False)

    result = validator.validate(tmp_path)
    assert result["status"] == "BLOCKED"
    assert result["checks"]["website_feed_matches_full_scan_eligible"] is False
