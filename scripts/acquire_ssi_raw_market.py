#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import date, timedelta
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.stockradar.ssi_raw_adapter import (
    SSIAuthenticatedSession,
    SSICredentials,
    SSIRawMarketAdapter,
    acquire_market_history,
    write_ohlcv,
    write_security_master,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Acquire raw HOSE identity/ICB and OHLCV from SSI FastConnect for StockRadar internal computation."
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--from-date", default=None, help="YYYY-MM-DD. Default: 3 calendar years ago.")
    parser.add_argument("--to-date", default=None, help="YYYY-MM-DD. Default: today.")
    parser.add_argument("--minimum-daily-bars", type=int, default=252)
    parser.add_argument("--include-5m", action="store_true")
    parser.add_argument("--intraday-from-date", default=None, help="YYYY-MM-DD; default: 10 calendar days ago.")
    return parser.parse_args()


def parse_date(value: str | None, fallback: date) -> date:
    if value is None:
        return fallback
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise SystemExit(f"invalid date {value!r}; expected YYYY-MM-DD") from error


def main() -> None:
    args = parse_args()
    today = date.today()
    start = parse_date(args.from_date, today - timedelta(days=365 * 3 + 30))
    end = parse_date(args.to_date, today)
    if start > end:
        raise SystemExit("--from-date must not be after --to-date")
    if args.minimum_daily_bars < 210:
        raise SystemExit("--minimum-daily-bars must be at least 210")

    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    credentials = SSICredentials.from_env()

    with SSIAuthenticatedSession(credentials) as session:
        adapter = SSIRawMarketAdapter(session.market_data, hose_board=session.hose_board)
        securities, daily = acquire_market_history(
            adapter=adapter,
            from_date=start,
            to_date=end,
            minimum_daily_bars=args.minimum_daily_bars,
        )
        write_security_master(output / "security_master.csv", securities)
        write_ohlcv(output / "ohlcv.csv", daily)

        intraday_count = 0
        if args.include_5m:
            intraday_start = parse_date(args.intraday_from_date, end - timedelta(days=10))
            intraday_rows = []
            for security in securities:
                intraday_rows.extend(adapter.fetch_5m_ohlcv(security.ticker, intraday_start, end))
            write_ohlcv(output / "intraday_5m.csv", intraday_rows)
            intraday_count = len(intraday_rows)

    metadata = {
        "adapter_version": "STOCKRADAR_SSI_RAW_ADAPTER_V1",
        "source": "SSI_FASTCONNECT_V3_RAW_MARKET",
        "external_input_role": "RAW_INPUT_ONLY",
        "external_scores_accepted": False,
        "exchange": "HOSE",
        "from_date": start.isoformat(),
        "to_date": end.isoformat(),
        "security_count": len(securities),
        "daily_ohlcv_rows": len(daily),
        "intraday_5m_rows": intraday_count,
        "credentials_persisted": False,
        "downstream_calculation_origin": "STOCKRADAR_ENGINE",
    }
    (output / "ssi_raw_market_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"SSI raw market acquisition complete: {len(securities)} HOSE stocks, "
        f"{len(daily)} daily bars, {intraday_count} 5m bars. "
        "No provider score/rank/recommendation was ingested."
    )


if __name__ == "__main__":
    main()
