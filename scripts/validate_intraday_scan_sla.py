"""Validate observed data at an explicit checkpoint; a cron is never scan evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

TZ = ZoneInfo("Asia/Ho_Chi_Minh")
CHECKPOINTS = ("10:30", "11:15", "13:30", "14:15")


def parse_dt(value):
    try:
        ts = pd.Timestamp(value)
        if pd.isna(ts):
            return pd.NaT
        return ts.tz_localize(TZ) if ts.tzinfo is None else ts.tz_convert(TZ)
    except (ValueError, TypeError):
        return pd.NaT


def boolish(value):
    return str(value).strip().lower() in {"true", "1"}


def validate(args) -> dict:
    now = parse_dt(args.now) if args.now else pd.Timestamp.now(tz=TZ)
    if pd.isna(now):
        raise ValueError("Invalid evaluation time")
    checkpoint = args.checkpoint or "EOD_RESEARCH"
    is_intraday = checkpoint in CHECKPOINTS
    market = json.loads(Path(args.market_coverage).read_text(encoding="utf-8"))
    fundamentals = json.loads(Path(args.fundamental_coverage).read_text(encoding="utf-8"))
    qa = json.loads(Path(args.scanner_qa).read_text(encoding="utf-8"))
    scanner = pd.read_csv(args.scanner)
    intraday = pd.read_csv(args.intraday, usecols=["ticker", "timestamp"])
    master = pd.read_csv(args.security_master)
    for frame in (scanner, intraday, master):
        frame["ticker"] = frame["ticker"].astype(str).str.strip().str.upper()
    canonical = set(master.ticker)
    expected = len(canonical)
    market_time = parse_dt(market.get("as_of"))
    fundamental_time = parse_dt(fundamentals.get("as_of"))
    collector_age = (now-market_time).total_seconds()/60 if pd.notna(market_time) else None
    fundamental_age = (now-fundamental_time).total_seconds()/3600 if pd.notna(fundamental_time) else None
    intraday["timestamp"] = intraday.timestamp.map(parse_dt)
    invalid_bars = intraday.timestamp.isna()
    future_bars = intraday.timestamp > now
    last_bars = intraday.loc[~invalid_bars & ~future_bars].groupby("ticker").timestamp.max()
    liquid = set(scanner.loc[scanner.get("liquidity_pass_500k", pd.Series(False, index=scanner.index)).map(boolish), "ticker"])
    issues = {}
    for ticker in sorted(canonical):
        ts = last_bars.get(ticker, pd.NaT)
        if pd.isna(ts):
            issues[ticker] = "NO_INTRADAY_BAR"
        elif ts.date() != now.date():
            issues[ticker] = "PREVIOUS_SESSION"
        elif (now-ts).total_seconds() > 20*60:
            issues[ticker] = "STALE_INTRADAY_BAR"
    stale_liquid = sorted(liquid & issues.keys())
    source_times = pd.to_datetime(scanner.get("source_time_ms", pd.Series(index=scanner.index, dtype=float)), unit="ms", errors="coerce", utc=True)
    quote_age = (now-source_times).dt.total_seconds()/60
    bad_quotes = sorted(set(scanner.loc[~quote_age.between(0, 20) | (source_times.dt.tz_convert(TZ).dt.date != now.date()), "ticker"]) & liquid)
    source = str(market.get("source") or "")
    assertions = {
        "canonical_master_valid": expected > 0 and len(master) == expected and master.ticker.str.fullmatch(r"(?=.*[A-Z])[A-Z0-9]{3}").all(),
        "master_hose_only": "exchange" in master and master.exchange.eq("HOSE").all(),
        "scanner_exact_master": len(scanner) == expected and set(scanner.ticker) == canonical,
        "market_exact_master_count": int(market.get("universe_count") or 0) == expected,
        "qa_exact_master_count": int(qa.get("canonical_hose_count") or 0) == expected,
        "no_foreign_intraday_ticker": set(intraday.ticker) <= canonical,
        "source_identified_non_mock": bool(source) and not any(x in source.upper() for x in ("MOCK", "DEMO", "FIXTURE", "SAMPLE")),
        "daily_coverage_ge_99pct": expected > 0 and int(market.get("daily_covered") or 0)/expected >= .99,
        "board_coverage_ge_99pct": expected > 0 and int(market.get("board_covered") or 0)/expected >= .99,
        "collector_age_le_20m": collector_age is not None and 0 <= collector_age <= 20,
        "fundamentals_age_le_72h": fundamental_age is not None and 0 <= fundamental_age <= 72,
        "fundamental_coverage_ge_99pct": expected > 0 and int(fundamentals.get("finance_tickers_covered") or 0)/expected >= .99,
        "no_invalid_or_future_bars": not (invalid_bars | future_bars).any(),
        "bootstrap_public_gate_closed": qa.get("public_gate", {}).get("allowed") is False,
    }
    research_ready = all(bool(v) for v in assertions.values())
    delay = None
    if is_intraday:
        target = now.normalize()+pd.Timedelta(hours=int(checkpoint[:2]), minutes=int(checkpoint[3:]))
        delay = (now-target).total_seconds()/60
    intraday_assertions = {
        "explicit_intraday_checkpoint": is_intraday,
        "weekday_session": now.weekday() < 5,
        "checkpoint_delay_le_20m": delay is not None and 0 <= delay <= 20,
        "liquid_set_known": "liquidity_pass_500k" in scanner and bool(liquid),
        "every_liquid_bar_current_and_fresh": not stale_liquid,
        "every_liquid_quote_current_and_fresh": not bad_quotes,
    }
    return {
        "schema_version": "STOCKRADAR_INTRADAY_SLA_V2",
        "checked_at": now.isoformat(), "checkpoint": checkpoint,
        "internal_research_ready": research_ready,
        "internal_scan_ready": research_ready and all(intraday_assertions.values()),
        "public_action_allowed": False, "canonical_hose_count": expected,
        "collector_age_minutes": collector_age, "fundamental_age_hours": fundamental_age,
        "checkpoint_delay_minutes": delay,
        "ticker_freshness_issues": issues, "stale_liquid_intraday_tickers": stale_liquid,
        "stale_liquid_quote_tickers": bad_quotes,
        "assertions": {k: bool(v) for k, v in assertions.items()},
        "intraday_assertions": intraday_assertions,
        "note": "EOD/manual/research runs never prove an intraday checkpoint. Current-session bars are required even on a weekday; exchange holiday, rights, compliance and publication gates remain separate.",
    }


def main() -> None:
    p = argparse.ArgumentParser()
    for name in ("market-coverage", "fundamental-coverage", "scanner-qa", "scanner", "intraday", "security-master", "output"):
        p.add_argument("--"+name, required=True)
    p.add_argument("--checkpoint", choices=(*CHECKPOINTS, "EOD_RESEARCH"), default="EOD_RESEARCH")
    p.add_argument("--now")
    args = p.parse_args()
    result = validate(args)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    passed = result["internal_scan_ready"] if args.checkpoint in CHECKPOINTS else result["internal_research_ready"]
    raise SystemExit(0 if passed else 2)


if __name__ == "__main__":
    main()
