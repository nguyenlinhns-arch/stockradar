from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

EXPECTED_HOSE = 405
REQUIRED_FILES = {
    "scanner": "stockradar_scanner_master_405_2026-09-04.csv",
    "valuation": "stockradar_valuation_bootstrap_405_2026-09-04.csv",
    "website_feed": "stockradar_website_feed_internal_2026-09-04.csv",
    "runtime_manifest": "stockradar_runtime_manifest_2026-09-04.json",
}


def _read_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "ticker" not in df.columns:
        raise ValueError(f"{path.name}: missing ticker column")
    df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()
    if df["ticker"].duplicated().any():
        dup = df.loc[df["ticker"].duplicated(), "ticker"].head(10).tolist()
        raise ValueError(f"{path.name}: duplicate tickers: {dup}")
    return df


def validate(root: Path) -> dict:
    missing_files = [name for name in REQUIRED_FILES.values() if not (root / name).exists()]
    if missing_files:
        return {"status": "BLOCKED", "reason": "MISSING_FILES", "missing_files": missing_files}

    scanner = _read_csv(root / REQUIRED_FILES["scanner"])
    valuation = _read_csv(root / REQUIRED_FILES["valuation"])
    website = _read_csv(root / REQUIRED_FILES["website_feed"])
    manifest = json.loads((root / REQUIRED_FILES["runtime_manifest"]).read_text(encoding="utf-8"))

    full_scan = scanner["full_scan_eligible"] if "full_scan_eligible" in scanner.columns else pd.Series(False, index=scanner.index)
    eligible_set = set(scanner.loc[full_scan.fillna(False).astype(bool), "ticker"])
    website_set = set(website["ticker"])

    checks = {
        "scanner_rows_405": len(scanner) == EXPECTED_HOSE,
        "valuation_rows_405": len(valuation) == EXPECTED_HOSE,
        "scanner_unique_405": scanner["ticker"].nunique() == EXPECTED_HOSE,
        "valuation_unique_405": valuation["ticker"].nunique() == EXPECTED_HOSE,
        "scanner_valuation_same_universe": set(scanner["ticker"]) == set(valuation["ticker"]),
        "website_feed_unique": website["ticker"].nunique() == len(website),
        "website_feed_subset_of_scanner": website_set.issubset(set(scanner["ticker"])),
        "website_feed_matches_full_scan_eligible": website_set == eligible_set,
        "manifest_hose_405": int(manifest.get("canonical_universe", 0)) == EXPECTED_HOSE,
        "public_gate_closed": manifest.get("public_feed_allowed") is False,
    }

    required_scanner_columns = {
        "ticker",
        "price",
        "vol20",
        "stage",
        "stockradar_score",
        "candidate_setup",
        "rvol_progress_adjusted",
        "same_time_volume_ratio",
        "pivot20",
        "roe_ttm_pct",
        "upside_to_base_pct",
        "liquidity_pass_500k",
        "full_scan_eligible",
    }
    checks["scanner_core_columns"] = required_scanner_columns.issubset(scanner.columns)

    required_website_columns = {
        "ticker",
        "price",
        "stockradar_score",
        "candidate_setup",
        "publication_gate",
    }
    checks["website_feed_core_columns"] = required_website_columns.issubset(website.columns)

    if "publication_gate" in website.columns and manifest.get("public_feed_allowed") is False:
        checks["website_feed_fail_closed"] = website["publication_gate"].astype(str).str.startswith("BLOCKED").all()
    else:
        checks["website_feed_fail_closed"] = False

    forbidden_public_columns = {
        "personal_priority",
        "priority_rank_personal",
        "owner_portfolio",
        "my_ticker",
        "private_note",
    }
    checks["website_feed_no_personal_columns"] = not bool(forbidden_public_columns & set(website.columns))
    checks = {key: bool(value) for key, value in checks.items()}

    passed = all(checks.values())
    return {
        "status": "PASS_INTERNAL" if passed else "BLOCKED",
        "canonical_hose_count": EXPECTED_HOSE,
        "scanner_rows": int(len(scanner)),
        "valuation_rows": int(len(valuation)),
        "eligible_feed_rows": int(len(eligible_set)),
        "website_feed_rows": int(len(website_set)),
        "checks": checks,
        "public_publication_authorized": False,
        "note": "PASS_INTERNAL means the private scanner bundle is structurally usable. Publication remains gated by source rights, freshness, corporate-action reconciliation, compliance and production approval.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a private StockRadar HOSE scanner bundle without publishing raw data.")
    parser.add_argument("bundle_dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = validate(args.bundle_dir)
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    raise SystemExit(0 if result["status"] == "PASS_INTERNAL" else 2)


if __name__ == "__main__":
    main()
