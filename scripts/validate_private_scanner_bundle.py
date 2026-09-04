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

    checks = {
        "scanner_rows_405": len(scanner) == EXPECTED_HOSE,
        "valuation_rows_405": len(valuation) == EXPECTED_HOSE,
        "website_feed_rows_405": len(website) == EXPECTED_HOSE,
        "scanner_unique_405": scanner["ticker"].nunique() == EXPECTED_HOSE,
        "valuation_unique_405": valuation["ticker"].nunique() == EXPECTED_HOSE,
        "website_unique_405": website["ticker"].nunique() == EXPECTED_HOSE,
        "scanner_valuation_same_universe": set(scanner["ticker"]) == set(valuation["ticker"]),
        "scanner_website_same_universe": set(scanner["ticker"]) == set(website["ticker"]),
        "manifest_hose_405": int(manifest.get("canonical_hose_count", 0)) == EXPECTED_HOSE,
        "public_gate_closed": manifest.get("public_gate", {}).get("allowed") is False,
    }

    # Internal scanner must retain core decision inputs. This does not authorize publication.
    required_scanner_columns = {
        "ticker",
        "price",
        "vol20",
        "stage",
        "stockradar_score_v2",
        "setup_internal",
        "action_candidate_internal",
        "buy_zone_low_internal",
        "buy_zone_high_internal",
        "stop_loss_internal",
        "target_near_rr2_internal",
    }
    checks["scanner_core_columns"] = required_scanner_columns.issubset(scanner.columns)

    # Public-facing cache must not leak explicit personal-priority fields.
    forbidden_public_columns = {
        "personal_priority",
        "priority_rank_personal",
        "owner_portfolio",
        "my_ticker",
        "private_note",
    }
    checks["website_feed_no_personal_columns"] = not bool(forbidden_public_columns & set(website.columns))

    passed = all(checks.values())
    return {
        "status": "PASS_INTERNAL" if passed else "BLOCKED",
        "canonical_hose_count": EXPECTED_HOSE,
        "checks": checks,
        "public_publication_authorized": False,
        "note": "PASS_INTERNAL only means the private scanner bundle is structurally usable. Publication remains separately gated by source rights, freshness, compliance and production approval.",
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
