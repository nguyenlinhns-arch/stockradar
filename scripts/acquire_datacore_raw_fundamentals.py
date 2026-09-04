#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.stockradar.datacore_raw_fundamentals import (
    DATACORE_ANNUAL_DATASET,
    DATACORE_QUARTERLY_DATASET,
    DATACORE_RAW_FUNDAMENTALS_VERSION,
    DataCoreAuthenticatedSession,
    DataCoreCredentials,
    acquire_fundamentals,
    read_hose_shares,
    write_fundamentals,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Acquire DataCore financial-statement line items for StockRadar internal computation."
    )
    parser.add_argument("--security-master", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--minimum-annual-periods", type=int, default=2)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.minimum_annual_periods < 2:
        raise SystemExit("--minimum-annual-periods must be at least 2")
    shares = read_hose_shares(args.security_master)
    credentials = DataCoreCredentials.from_env()
    with DataCoreAuthenticatedSession(credentials) as session:
        rows = acquire_fundamentals(
            client=session.client,
            shares_by_ticker=shares,
            minimum_annual_periods=args.minimum_annual_periods,
        )

    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    write_fundamentals(output / "fundamentals.csv", rows)
    metadata = {
        "adapter_version": DATACORE_RAW_FUNDAMENTALS_VERSION,
        "source": "DATACORE_FINANCIAL_STATEMENTS",
        "datasets": [DATACORE_ANNUAL_DATASET, DATACORE_QUARTERLY_DATASET],
        "external_input_role": "RAW_FINANCIAL_STATEMENT_LINE_ITEMS_ONLY",
        "external_scores_accepted": False,
        "hose_tickers_expected": len(shares),
        "normalized_rows": len(rows),
        "credentials_persisted": False,
        "downstream_calculation_origin": "STOCKRADAR_ENGINE",
        "publication_rights_assumed": False,
    }
    (output / "datacore_raw_fundamentals_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"DataCore raw financial line-items acquired: {len(rows)} rows / {len(shares)} HOSE tickers. "
        "No provider ratios, score, rank, valuation or recommendation was ingested."
    )


if __name__ == "__main__":
    main()
