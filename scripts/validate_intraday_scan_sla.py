from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

TZ = ZoneInfo("Asia/Ho_Chi_Minh")
EXPECTED_HOSE = 405
CHECKPOINTS = ((10, 30), (11, 15), (13, 30), (14, 15))


def parse_dt(value):
    dt = pd.to_datetime(value, errors="coerce", utc=True)
    if pd.isna(dt):
        return pd.NaT
    return dt.tz_convert(TZ)


def checkpoint_label(now: datetime) -> str:
    minutes = now.hour * 60 + now.minute
    nearest = min(CHECKPOINTS, key=lambda hm: abs(minutes - (hm[0] * 60 + hm[1])))
    return f"{nearest[0]:02d}:{nearest[1]:02d}"


def validate(args) -> dict:
    now = pd.Timestamp(args.now).tz_localize(TZ) if args.now else pd.Timestamp.now(tz=TZ)
    market = json.loads(Path(args.market_coverage).read_text(encoding="utf-8"))
    fundamentals = json.loads(Path(args.fundamental_coverage).read_text(encoding="utf-8"))
    qa = json.loads(Path(args.scanner_qa).read_text(encoding="utf-8"))
    scanner = pd.read_csv(args.scanner)
    intraday = pd.read_csv(args.intraday, usecols=["ticker", "timestamp"])

    market_time = parse_dt(market.get("as_of"))
    fundamental_time = parse_dt(fundamentals.get("as_of"))
    collector_age_min = (now - market_time).total_seconds() / 60 if pd.notna(market_time) else None
    fundamental_age_hours = (now - fundamental_time).total_seconds() / 3600 if pd.notna(fundamental_time) else None

    scanner["ticker"] = scanner["ticker"].astype(str).str.strip().str.upper()
    intraday["ticker"] = intraday["ticker"].astype(str).str.strip().str.upper()
    intraday["timestamp"] = pd.to_datetime(intraday["timestamp"], errors="coerce")
    current_day = now.date()
    last_bar_by_ticker = intraday.dropna(subset=["timestamp"]).groupby("ticker")["timestamp"].max()
    intraday_tickers = set(last_bar_by_ticker.index)
    all_tickers = set(scanner["ticker"])
    missing = sorted(all_tickers - intraday_tickers)
    liquid = set(scanner.loc[scanner.get("liquidity_pass_500k", False).fillna(False).astype(bool), "ticker"])
    missing_liquid = sorted(liquid - intraday_tickers)

    max_intra = intraday["timestamp"].max() if not intraday.empty else pd.NaT
    latest_intra_age_min = None
    if pd.notna(max_intra):
        ts = pd.Timestamp(max_intra)
        if ts.tzinfo is None:
            ts = ts.tz_localize(TZ)
        else:
            ts = ts.tz_convert(TZ)
        latest_intra_age_min = (now - ts).total_seconds() / 60

    assertions = {
        "canonical_hose_405": int(qa.get("canonical_hose_count") or 0) == EXPECTED_HOSE,
        "market_universe_405": int(market.get("universe_count") or 0) >= EXPECTED_HOSE,
        "daily_coverage_ge_99pct": int(market.get("daily_covered") or 0) >= 401,
        "board_coverage_ge_99pct": int(market.get("board_covered") or 0) >= 401,
        "collector_age_le_20m": collector_age_min is not None and -2 <= collector_age_min <= 20,
        "fundamentals_age_le_72h": fundamental_age_hours is not None and -1 <= fundamental_age_hours <= 72,
        "fundamental_coverage_ge_99pct": int(fundamentals.get("finance_tickers_covered") or 0) >= 401,
        "no_liquid_ticker_missing_intraday": len(missing_liquid) == 0,
        "bootstrap_public_gate_closed": qa.get("public_gate", {}).get("allowed") is False,
    }

    # The collector can legitimately miss non-liquid/sparse listings. It cannot miss a liquid stock and still alert.
    internal_ready = all(bool(v) for v in assertions.values())
    result = {
        "schema_version": "STOCKRADAR_INTRADAY_SLA_V1",
        "checked_at": now.isoformat(),
        "checkpoint": args.checkpoint or checkpoint_label(now.to_pydatetime()),
        "internal_scan_ready": internal_ready,
        "public_action_allowed": False,
        "collector_age_minutes": round(collector_age_min, 2) if collector_age_min is not None else None,
        "fundamental_age_hours": round(fundamental_age_hours, 2) if fundamental_age_hours is not None else None,
        "latest_intraday_age_minutes": round(latest_intra_age_min, 2) if latest_intra_age_min is not None else None,
        "intraday_ticker_count": len(intraday_tickers),
        "missing_intraday_tickers": missing,
        "missing_liquid_intraday_tickers": missing_liquid,
        "assertions": assertions,
        "note": "Internal scan readiness does not authorize public publication; data-rights/compliance/manifest gates remain separate.",
    }
    return result


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--market-coverage", required=True)
    p.add_argument("--fundamental-coverage", required=True)
    p.add_argument("--scanner-qa", required=True)
    p.add_argument("--scanner", required=True)
    p.add_argument("--intraday", required=True)
    p.add_argument("--checkpoint")
    p.add_argument("--now")
    p.add_argument("--output", required=True)
    args = p.parse_args()
    result = validate(args)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(0 if result["internal_scan_ready"] else 2)


if __name__ == "__main__":
    main()
