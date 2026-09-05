"""Private, versioned data layer. No provider calls or personal lists in serving paths."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3

import pandas as pd

from .internal_features import RawBar, compute_technical_features


SCHEMA_VERSION = "stockradar.data.v1"


def number(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (ValueError, TypeError):
        return None


def read_frame(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        return pd.DataFrame(data.get("items", data) if isinstance(data, dict) else data)
    return pd.read_csv(path, encoding="utf-8-sig")


def keyed(frame: pd.DataFrame, universe: set[str]) -> dict:
    frame = frame.rename(columns={"symbol": "ticker"}).copy()
    if "ticker" not in frame:
        raise ValueError("MISSING_TICKER")
    frame["ticker"] = frame.ticker.astype(str).str.strip().str.upper()
    if frame.ticker.duplicated().any():
        raise ValueError("DUPLICATE_TICKER")
    if not set(frame.ticker).issubset(universe):
        raise ValueError("NON_HOSE_TICKER")
    return {r["ticker"]: r for r in frame.where(pd.notna(frame), None).to_dict("records")}


def validate_history(frame: pd.DataFrame, universe: set[str], as_of: str):
    x = frame.rename(columns={"symbol": "ticker", "date": "timestamp"}).copy()
    required = {"ticker", "timestamp", "open", "high", "low", "close", "volume"}
    if not required.issubset(x.columns):
        raise ValueError("MISSING_OHLC_COLUMNS")
    x["ticker"] = x.ticker.astype(str).str.strip().str.upper()
    if not set(x.ticker).issubset(universe):
        raise ValueError("NON_HOSE_TICKER")
    dates = pd.to_datetime(x.timestamp, errors="coerce", utc=True)
    x["date"] = dates.dt.strftime("%Y-%m-%d")
    if dates.isna().any():
        raise ValueError("MISSING_OR_INVALID_TIMESTAMP")
    if (x.date > as_of).any():
        raise ValueError("FUTURE_TRADING_DATE")
    if x.duplicated(["ticker", "date"]).any():
        raise ValueError("DUPLICATE_TRADING_DATE")
    for column in ("open", "high", "low", "close", "volume"):
        x[column] = pd.to_numeric(x[column], errors="coerce")
    valid = x[["open", "high", "low", "close", "volume"]].notna().all(axis=1)
    valid &= x[["open", "high", "low", "close", "volume"]].map(math.isfinite).all(axis=1)
    valid &= (x[["open", "high", "low", "close"]] > 0).all(axis=1) & (x.volume >= 0)
    valid &= x.high >= x[["open", "close", "low"]].max(axis=1)
    valid &= x.low <= x[["open", "close", "high"]].min(axis=1)
    issues = x.loc[~valid, ["ticker", "date"]].to_dict("records")
    # Invalid rows are quarantined. Their tickers are never marked fully current.
    return x[valid].sort_values(["ticker", "date"]), issues


def build_data_layer(*, universe: set[str], history: pd.DataFrame, technical: pd.DataFrame,
                     fundamental: pd.DataFrame, valuation: pd.DataFrame,
                     as_of: str, sources: list[dict], output: Path):
    if not universe or any(not re.fullmatch(r"(?=.*[A-Z])[A-Z0-9]{3}", t) for t in universe):
        raise ValueError("INVALID_HOSE_UNIVERSE")
    if as_of > datetime.now(timezone.utc).date().isoformat():
        raise ValueError("FUTURE_AS_OF")
    frames = [keyed(frame, universe) for frame in (technical, fundamental, valuation)]
    bars, issues = validate_history(history, universe, as_of)
    generated_at = datetime.now(timezone.utc).isoformat()
    bad = {row["ticker"] for row in issues}
    records = []
    for ticker, group in bars.groupby("ticker", sort=True):
        t, f, v = (mapping.get(ticker, {}) for mapping in frames)
        last = group.iloc[-1]
        n = lambda key, row=f: number(row.get(key))
        price = float(last.close)
        tech = {key: (number(value) if key not in {"stage", "ichimoku_state", "source", "rights_publication"} and not isinstance(value, bool) else value) for key, value in t.items() if key != "ticker"}
        # Reuse the existing StockRadar indicator engine, never a separate signal model.
        if len(group) >= 252 and ticker not in bad:
            raw = [RawBar(str(r.date), r.open, r.high, r.low, r.close, r.volume) for r in group.itertuples()]
            computed = asdict(compute_technical_features(raw))
            # Existing research/scanner decisions remain canonical. Persist computations as evidence.
            tech["computed_indicators"] = computed
            for key in ("bollinger_upper", "bollinger_lower", "bollinger_middle", "high_52w", "low_52w"):
                tech[key] = computed[key]
        for period in (10, 20, 50, 150, 200):
            tech[f"ma{period}"] = float(group.close.tail(period).mean()) if len(group) >= period else None
        tech["volume"] = float(last.volume)
        tech["vol20"] = float(group.volume.iloc[-21:-1].mean()) if len(group) >= 21 else None
        tech["vol50"] = float(group.volume.iloc[-51:-1].mean()) if len(group) >= 51 else None
        tech["rvol"] = float(last.volume) / tech["vol20"] if tech["vol20"] else None
        tech["volume_mode"] = "EOD"
        tech["same_time_volume"] = None
        # Progress-adjusted values belong to intraday snapshots, not the closing bar.
        tech["rvol_progress_adjusted"] = None
        tech["same_time_volume_ratio"] = None
        tech["max_down_volume10"] = n("max_down_volume_10", t)
        tech["avg_volume_20"] = tech["vol20"]
        tech["avg_volume_50"] = tech["vol50"]
        # Source conventions: positive distance means above pivot, negative means below.
        pivot = n("pivot20", t)
        tech["distance_to_pivot_pct"] = (price / pivot - 1) * 100 if pivot else None
        fair = n("fair_value_bootstrap_base", v)
        valuation_data = {
            "pe": n("pe_current_calc", v), "pb": n("pb_current_calc", v),
            "forward_pe": None, "peg": None, "ev_ebitda": n("ev_ebitda_provider_period", v),
            "fair_value": fair, "bear": n("fair_value_bootstrap_bear", v),
            "base": fair, "bull": n("fair_value_bootstrap_bull", v),
            "mos": (fair - price) / fair * 100 if fair and fair > 0 else None,
            "upside": (fair / price - 1) * 100 if fair else None,
            "model_status": str(v.get("valuation_model_status") or "INSUFFICIENT_DATA"),
            "assumptions_verified": False,
        }
        quality = "error" if ticker in bad else "updated" if last.date == as_of else "stale"
        records.append({
            "symbol": ticker, "exchange": "HOSE", "as_of_date": str(last.date),
            "updated_at": generated_at, "updated_at_basis": "ETL_GENERATED_AT", "data_source": sources,
            "data_quality": quality, "price": price,
            "quote": {key: float(last[key]) for key in ("open", "high", "low", "close", "volume")},
            "technical_detail": tech,
            "fundamental_detail": {**{k: number(val) for k, val in f.items() if k not in {"ticker", "source", "rights_publication", "latest_period_end", "fundamental_feature_status"}},
                                   "roe_pct": n("roe_ttm_pct"), "roa_pct": n("roa_ttm_pct"),
                                   "eps": n("eps_ttm"), "profit_growth_yoy_pct": None,
                                   "eps_growth_yoy_pct": None, "period_end": str(f.get("latest_period_end") or "")},
            "valuation_detail": valuation_data,
            "history": {"from": str(group.date.min()), "to": str(last.date), "bars": len(group),
                        "recent": group.tail(20)[["date", "open", "high", "low", "close", "volume"]].to_dict("records")},
            "public_action_allowed": False,
        })
    payload = {"schema_version": SCHEMA_VERSION, "as_of_date": as_of, "sources": sources, "records": records}
    encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False, sort_keys=True)
    snapshot_id = "data-" + hashlib.sha256(encoded.encode()).hexdigest()[:24]
    payload["snapshot_id"] = snapshot_id
    output.mkdir(parents=True, exist_ok=True)
    (output / "data-layer.json").write_text(json.dumps(payload, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    # Local raw history stays indexed and private; browsers never download the full universe.
    connection = sqlite3.connect(output / "history.sqlite")
    try:
        bars[["ticker", "date", "open", "high", "low", "close", "volume"]].to_sql("price_history", connection, if_exists="replace", index=False)
        connection.execute("create unique index price_history_ticker_date on price_history(ticker,date)")
        connection.commit()
    finally:
        connection.close()
    qa = {"snapshot_id": snapshot_id, "hose_count": len(records), "history_rows": len(bars),
          "history_from": str(bars.date.min()), "history_to": str(bars.date.max()),
          "quarantined_bars": len(issues), "quarantined_tickers": len(bad),
          "missing_tickers": sorted(universe - {r["symbol"] for r in records}),
          "status_counts": {s: sum(r["data_quality"] == s for r in records) for s in ("updated", "stale", "error")}}
    (output / "qa.json").write_text(json.dumps(qa, indent=2), encoding="utf-8")
    return payload, qa
