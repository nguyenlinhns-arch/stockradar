#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

EXPECTED_HOSE = 405
SECTOR_OVERRIDES = {
    "ADG": "Truyền thông - Quảng cáo",
    "CLC": "Hàng tiêu dùng",
    "YEG": "Truyền thông - Giải trí",
}


def parse_payload(value):
    try:
        obj = json.loads(value) if isinstance(value, str) else value
    except Exception:
        return []
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        return [obj]
    return []


def scale(value, low, high):
    if pd.isna(value) or high <= low:
        return 50.0
    return float(np.clip((float(value) - low) / (high - low) * 100.0, 0.0, 100.0))


def latest_date(items, keys):
    dates = []
    for item in items:
        if not isinstance(item, dict):
            continue
        for key in keys:
            d = pd.to_datetime(item.get(key), errors="coerce")
            if pd.notna(d):
                dates.append(d)
    return max(dates) if dates else pd.NaT


def compute_market_regime(market, vni):
    vni = vni.copy()
    vni["timestamp"] = pd.to_datetime(vni["timestamp"], errors="coerce")
    vni = vni.dropna(subset=["timestamp"]).sort_values("timestamp")
    for n in (50, 150, 200):
        vni[f"ma{n}"] = pd.to_numeric(vni["close"], errors="coerce").rolling(n).mean()
    last = vni.iloc[-1]
    ma200_slope = 0.0
    if len(vni) >= 221 and pd.notna(vni.iloc[-21]["ma200"]):
        ma200_slope = float(last["ma200"] - vni.iloc[-21]["ma200"])
    checks = [
        last["close"] > last["ma50"],
        last["ma50"] > last["ma150"],
        last["ma150"] > last["ma200"],
        ma200_slope > 0,
    ]
    index_score = sum(bool(x) for x in checks) / 4 * 100
    n = max(int(market["universe_count"]), 1)
    breadth_score = (
        0.25 * market["advancers"] / n * 100
        + 0.30 * market["above_ma50"] / n * 100
        + 0.30 * market["above_ma200"] / n * 100
        + 0.15 * market["stage2_count"] / n * 100
    )
    score = round(0.40 * index_score + 0.60 * breadth_score, 2)
    if score >= 70:
        regime = "THUAN_LOI"
    elif score >= 55:
        regime = "TICH_CUC_CO_CHON_LOC"
    elif score >= 40:
        regime = "PHAN_HOA_THAN_TRONG"
    else:
        regime = "RUI_RO_CAO"
    return score, regime, round(index_score, 2)


def compute_risk_features(ohlcv):
    ohlcv = ohlcv.copy()
    ohlcv["timestamp"] = pd.to_datetime(ohlcv["timestamp"], errors="coerce")
    ohlcv = ohlcv.dropna(subset=["timestamp"]).sort_values(["ticker", "timestamp"])
    rows = []
    for ticker, g in ohlcv.groupby("ticker", sort=False):
        g = g.sort_values("timestamp").copy()
        for c in ("high", "low", "close", "volume"):
            g[c] = pd.to_numeric(g[c], errors="coerce")
        g = g.dropna(subset=["high", "low", "close"])
        if g.empty:
            continue
        prev = g["close"].shift(1)
        tr = pd.concat([(g["high"] - g["low"]).abs(), (g["high"] - prev).abs(), (g["low"] - prev).abs()], axis=1).max(axis=1)
        close = float(g["close"].iloc[-1])
        atr20 = tr.tail(20).mean() if len(tr) >= 20 else np.nan
        ret = g["close"].pct_change()
        realized = ret.tail(20).std(ddof=0) * math.sqrt(20) * 100 if ret.tail(20).notna().sum() >= 10 else np.nan
        w = g.tail(60)
        dd = (w["close"] / w["close"].cummax() - 1) * 100
        rows.append({
            "ticker": ticker,
            "atr20_pct": atr20 / close * 100 if pd.notna(atr20) and close else np.nan,
            "realized_vol20_pct": realized,
            "max_drawdown60_pct": float(dd.min()) if not dd.empty else np.nan,
        })
    return pd.DataFrame(rows)


def build(args):
    scanner = pd.read_csv(args.scanner)
    status = pd.read_csv(args.status)
    ohlcv = pd.read_csv(args.ohlcv)
    news = pd.read_csv(args.news)
    events = pd.read_csv(args.events)
    vni = pd.read_csv(args.vnindex)
    with open(args.market_context, encoding="utf-8") as f:
        market = json.load(f)

    if scanner["ticker"].nunique() != EXPECTED_HOSE or len(scanner) != EXPECTED_HOSE:
        raise ValueError("scanner master must contain exactly 405 unique HOSE tickers")

    status["sector_v2"] = status.apply(lambda r: SECTOR_OVERRIDES.get(str(r["ticker"]), r.get("sector")), axis=1)
    intraday = pd.read_csv(args.intraday, usecols=["ticker"])
    intraday_set = set(intraday["ticker"].astype(str).str.upper().unique())

    news["items"] = news["payload"].map(parse_payload)
    news["news_count_raw"] = news["items"].map(len)
    news["latest_news_time"] = news["items"].map(lambda x: latest_date(x, ("PublishTime", "Date", "Time")))
    news["latest_news_title"] = news["items"].map(lambda x: x[0].get("Title", "") if x and isinstance(x[0], dict) else "")

    events["items"] = events["payload"].map(parse_payload)
    events["event_count_raw"] = events["items"].map(len)
    events["latest_event_time"] = events["items"].map(lambda x: latest_date(x, ("ReportDate", "GDKHQDate", "NDKCCDate", "Time", "PublishTime")))

    asof = pd.Timestamp(args.as_of)
    news["latest_news_age_days"] = (asof - news["latest_news_time"].dt.normalize()).dt.days
    events["latest_event_age_days"] = (asof - events["latest_event_time"].dt.normalize()).dt.days
    events["corporate_action_current_ready"] = events["latest_event_age_days"].between(0, 365, inclusive="both")

    market_score, market_regime, index_score = compute_market_regime(market, vni)
    risk = compute_risk_features(ohlcv)

    sec = status[["ticker", "sector_v2"]].merge(scanner[["ticker", "pct_change", "price", "ma50", "stage", "rs_percentile_6m"]], on="ticker", how="left")
    sec_rows = []
    for sector, g in sec.groupby("sector_v2", dropna=False):
        count = len(g)
        adv_pct = (g["pct_change"] > 0).sum() / count * 100
        above_pct = ((g["price"] > g["ma50"]) & g["ma50"].notna()).sum() / count * 100
        stage2_pct = g["stage"].eq("STAGE_2").sum() / count * 100
        rs = float(g["rs_percentile_6m"].mean()) if g["rs_percentile_6m"].notna().any() else 50.0
        raw = 0.35 * rs + 0.30 * above_pct + 0.20 * stage2_pct + 0.15 * adv_pct
        confidence = min(1.0, count / 5.0)
        score = 50 + (raw - 50) * confidence
        regime = "LEADING" if score >= 65 else "IMPROVING" if score >= 55 else "NEUTRAL" if score >= 45 else "WEAK" if score >= 35 else "LAGGING"
        sec_rows.append({"sector": sector, "count": count, "sector_strength_score": round(score, 2), "sector_regime": regime, "sector_confidence": round(confidence, 2)})
    sector_df = pd.DataFrame(sec_rows)
    sector_join = sector_df.rename(columns={"sector": "sector_join_v3"})

    out = scanner.merge(status[["ticker", "company_name_vi", "sector_v2", "daily_bar_count", "technical_data_ready", "fundamental_data_ready"]], on="ticker", how="left")
    out = out.merge(risk, on="ticker", how="left")
    out = out.merge(news[["ticker", "news_count_raw", "latest_news_time", "latest_news_age_days", "latest_news_title"]], on="ticker", how="left")
    out = out.merge(events[["ticker", "event_count_raw", "latest_event_time", "latest_event_age_days", "corporate_action_current_ready"]], on="ticker", how="left")
    out = out.merge(sector_join, left_on="sector_v2", right_on="sector_join_v3", how="left").drop(columns=["sector_join_v3"])

    out["intraday_5m_ready"] = out["ticker"].isin(intraday_set)
    out["market_score"] = market_score
    out["market_regime"] = market_regime
    out["valuation_ready"] = out["upside_to_base_pct"].notna()
    out["sector_ready"] = out["sector_strength_score"].notna()
    out["foreign_flow_snapshot_ready"] = out["foreign_buy_volume"].notna() & out["foreign_sell_volume"].notna()
    out["risk_features_ready"] = out[["atr20_pct", "realized_vol20_pct", "max_drawdown60_pct"]].notna().sum(axis=1) >= 2
    out["catalyst_data_ready"] = False
    out["catalyst_score"] = np.nan
    out["corporate_action_data_ready"] = out["corporate_action_current_ready"].fillna(False)

    out["data_quality_score"] = (
        25 * out["history_210d_pass"].fillna(False).astype(int)
        + 15 * out["intraday_5m_ready"].astype(int)
        + 20 * out["fundamental_data_ready"].fillna(False).astype(int)
        + 15 * out["valuation_ready"].astype(int)
        + 10 * out["sector_ready"].astype(int)
        + 10 * out["foreign_flow_snapshot_ready"].astype(int)
        + 5 * out["risk_features_ready"].astype(int)
    )

    risk_scores = []
    for _, r in out.iterrows():
        atr = scale(r["atr20_pct"], 1, 8)
        vol = scale(r["realized_vol20_pct"], 2, 20)
        dd = scale(abs(r["max_drawdown60_pct"]) if pd.notna(r["max_drawdown60_pct"]) else np.nan, 5, 30)
        vol20 = max(float(r["vol20"]) if pd.notna(r["vol20"]) else 1.0, 1.0)
        illiq = 100 - scale(math.log10(vol20), math.log10(100_000), math.log10(5_000_000))
        risk_scores.append(round(0.30 * atr + 0.20 * vol + 0.25 * dd + 0.25 * illiq, 2))
    out["risk_score"] = risk_scores
    out["radar_rank_score_v3"] = (0.72 * out["stockradar_score"] + 0.13 * out["sector_strength_score"].fillna(50) + 0.07 * market_score + 0.08 * (100 - out["risk_score"])).round(2)
    out["operational_candidate"] = out["full_scan_eligible"].fillna(False) & out["liquidity_pass_500k"].fillna(False) & out["sector_ready"] & (out["data_quality_score"] >= 80)
    out["action_gate_v3"] = np.where(~out["operational_candidate"], "BLOCKED_DATA_OR_LIQUIDITY", np.where(out["candidate_setup"].astype(str).eq("WATCH"), "WATCH", "RESEARCH_CANDIDATE_PENDING_EVENT_RIGHTS_GATE"))

    out.sort_values(["operational_candidate", "radar_rank_score_v3"], ascending=[False, False]).to_csv(args.output, index=False, encoding="utf-8-sig")
    sector_df.sort_values("sector_strength_score", ascending=False).to_csv(args.sector_output, index=False, encoding="utf-8-sig")

    manifest = {
        "generated_for": args.as_of,
        "canonical_hose": EXPECTED_HOSE,
        "market_regime": market_regime,
        "market_score": market_score,
        "index_trend_score": index_score,
        "coverage": {
            "daily_ohlcv": int(ohlcv["ticker"].nunique()),
            "intraday_5m": len(intraday_set),
            "technical_210": int(status["technical_data_ready"].fillna(False).sum()),
            "fundamentals": int(status["fundamental_data_ready"].fillna(False).sum()),
            "valuation_base": int(out["valuation_ready"].sum()),
            "sector": int(out["sector_ready"].sum()),
            "news_rows": len(news),
            "news_fresh_30d": int(out["latest_news_age_days"].between(0, 30, inclusive="both").sum()),
            "corporate_actions_current_365d": int(out["corporate_action_data_ready"].sum()),
        },
        "quality_gates": {
            "core_scanner": "PASS_INTERNAL",
            "market_sector_context": "PASS_INTERNAL",
            "catalyst_scoring": "BLOCKED_INSUFFICIENT_DEPTH",
            "corporate_actions": "BLOCKED_STALE_OR_EMPTY",
            "public_publication": "BLOCKED_SOURCE_RIGHTS_AND_COMPLIANCE",
        },
        "score_policy": {
            "radar_rank_score_v3": "72% core + 13% sector + 7% market + 8% inverse risk",
            "catalyst_weight": 0,
            "corporate_action_weight": 0,
        },
        "public_feed_allowed": False,
    }
    Path(args.manifest).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--scanner", required=True)
    p.add_argument("--status", required=True)
    p.add_argument("--ohlcv", required=True)
    p.add_argument("--intraday", required=True)
    p.add_argument("--news", required=True)
    p.add_argument("--events", required=True)
    p.add_argument("--market-context", required=True)
    p.add_argument("--vnindex", required=True)
    p.add_argument("--as-of", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--sector-output", required=True)
    p.add_argument("--manifest", required=True)
    build(p.parse_args())


if __name__ == "__main__":
    main()
