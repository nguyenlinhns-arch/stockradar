from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

SCHEMA_VERSION = "STOCKRADAR_SCANNER_V2.0"
EXPECTED_HOSE = 405
RIGHTS_BLOCK_VALUE = "BLOCKED_PENDING_TERMS_REVIEW"


def clip(value, low=0.0, high=100.0):
    if pd.isna(value):
        return np.nan
    return float(max(low, min(high, value)))


def scale(value, low, high):
    if pd.isna(value):
        return 0.0
    if high <= low:
        return 0.0
    return clip((float(value) - low) / (high - low) * 100.0)


def boolish(value):
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def valid_ticker(value):
    s = str(value or "").strip().upper()
    return len(s) == 3 and s.isascii() and s.isalnum() and any(c.isalpha() for c in s)


def load_unique(path, name):
    df = pd.read_csv(path)
    if "ticker" not in df.columns:
        raise ValueError(f"{name}: ticker column missing")
    df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()
    if not df["ticker"].map(valid_ticker).all():
        bad = df.loc[~df["ticker"].map(valid_ticker), "ticker"].tolist()[:10]
        raise ValueError(f"{name}: invalid ticker(s): {bad}")
    if df["ticker"].duplicated().any():
        dup = df.loc[df["ticker"].duplicated(), "ticker"].tolist()[:10]
        raise ValueError(f"{name}: duplicate ticker(s): {dup}")
    return df


def stage_score(stage):
    return {
        "STAGE_2": 100.0,
        "STAGE_1_TO_2": 90.0,
        "STAGE_1_OR_3": 45.0,
        "STAGE_1": 40.0,
        "STAGE_3": 25.0,
        "STAGE_4": 0.0,
    }.get(str(stage), 25.0)


def build(args):
    u = load_unique(args.universe, "universe")
    s = load_unique(args.security_master, "security_master")
    t = load_unique(args.technical, "technical")
    f = load_unique(args.fundamental, "fundamental")
    r = load_unique(args.relative_strength, "relative_strength")
    q = load_unique(args.snapshot, "snapshot")
    v = load_unique(args.valuation, "valuation")
    p = load_unique(args.company_profile, "company_profile") if args.company_profile else None

    canonical = set(u.ticker)
    if len(canonical) != EXPECTED_HOSE:
        raise ValueError(f"canonical HOSE must be {EXPECTED_HOSE}, got {len(canonical)}")

    coverage = {}
    for name, df in [("security_master", s), ("technical", t), ("fundamental", f), ("relative_strength", r), ("snapshot", q), ("valuation", v)]:
        covered = set(df.ticker) & canonical
        missing = sorted(canonical - covered)
        extra = sorted(set(df.ticker) - canonical)
        coverage[name] = {"covered": len(covered), "missing": missing, "extra": extra}

    base_cols = [c for c in ["ticker", "company_name_vi", "tradable_eligibility", "listing_status_semantics", "row_quality_flags"] if c in u.columns]
    out = u[base_cols].copy()
    out = out.merge(s[[c for c in ["ticker", "name", "sector", "exchange", "source"] if c in s.columns]], on="ticker", how="left", suffixes=("", "_sm"))
    if p is not None:
        profile_cols = [c for c in ["ticker", "leader_count", "foreign_ownership_profile_pct", "institutional_ownership_profile_pct", "major_shareholders_reported_pct", "top_shareholder_pct", "audit_firm"] if c in p.columns]
        out = out.merge(p[profile_cols], on="ticker", how="left")

    tech_cols = [
        "ticker", "price", "pct_change", "daily_bar_count", "ma10", "ma20", "ma50", "ma150", "ma200", "vol20",
        "current_cum_volume", "same_time_volume_ratio", "rvol_progress_adjusted", "max_down_volume_10", "same_time_max_down_volume_10",
        "pocket_pivot_volume_pass", "pivot20", "distance_to_pivot_pct", "stage", "ma200_slope_20d", "ichimoku_state",
        "bollinger_width_pct", "bollinger_squeeze", "volume_dry_up_5d", "vcp_contraction_score", "technical_history_eligible", "rights_publication"
    ]
    out = out.merge(t[[c for c in tech_cols if c in t.columns]], on="ticker", how="left", suffixes=("", "_technical"))

    fund_cols = [
        "ticker", "latest_period_end", "fundamental_feature_status", "rights_publication", "revenue_growth_yoy_pct", "gross_profit_growth_yoy_pct",
        "pbt_growth_yoy_pct", "equity_growth_yoy_pct", "gross_margin_pct", "eps_ttm", "bvps", "pe_provider_period", "pb_provider_period",
        "dividend_yield_pct", "debt_to_equity", "cash_flow_per_share", "ev_ebitda_provider_period", "roe_ttm_pct", "roa_ttm_pct",
        "pe_median_8q_provider", "pb_median_8q_provider", "revenue_growth_3y_avg_pct", "pbt_growth_3y_avg_pct", "equity_growth_3y_avg_pct",
        "bank_ldr_pct", "bank_loan_to_assets_pct", "bank_cir_pct", "bank_operating_profit_growth_yoy_pct", "bank_loan_loss_provision_ratio_pct"
    ]
    out = out.merge(f[[c for c in fund_cols if c in f.columns]], on="ticker", how="left", suffixes=("", "_fundamental"))
    out = out.merge(r, on="ticker", how="left")
    out = out.merge(v, on="ticker", how="left", suffixes=("", "_valuation"))

    snap_cols = [c for c in ["ticker", "foreign_buy_volume", "foreign_sell_volume", "source_time_ms", "match_status", "status", "total_volume"] if c in q.columns]
    out = out.merge(q[snap_cols], on="ticker", how="left")

    out["history_210d_pass"] = out["daily_bar_count"].fillna(0) >= 210
    out["liquidity_pass_500k"] = out["vol20"].fillna(0) >= 500_000
    out["fundamental_ready"] = out["fundamental_feature_status"].fillna("").eq("OK")
    out["technical_ready"] = out["technical_history_eligible"].map(boolish)
    out["full_scan_eligible"] = out[["history_210d_pass", "fundamental_ready", "technical_ready"]].all(axis=1)

    stage = out["stage"].map(stage_score)
    trend_checks = (
        (out["price"] > out["ma50"]).astype(float)
        + (out["ma50"] > out["ma150"]).astype(float)
        + (out["ma150"] > out["ma200"]).astype(float)
        + (out["ma200_slope_20d"] > 0).astype(float)
    ) / 4 * 100
    ich = out["ichimoku_state"].fillna("").map(lambda x: 100.0 if x == "ABOVE_KUMO" else 50.0 if x in {"IN_KUMO", "ABOVE_KIJUN"} else 15.0)
    contraction = out["vcp_contraction_score"].fillna(0).clip(0, 100)
    rs = out[["rs_percentile_3m", "rs_percentile_6m", "rs_percentile_12m"]].mean(axis=1, skipna=True).fillna(0).clip(0, 100)
    dry = out["volume_dry_up_5d"].map(boolish).map({True: 100.0, False: 0.0})
    out["technical_score_v2"] = (0.25 * stage + 0.30 * trend_checks + 0.15 * contraction + 0.20 * rs + 0.05 * ich + 0.05 * dry).round(2)

    rvol_score = out["rvol_progress_adjusted"].map(lambda x: scale(x, 0.6, 1.8))
    same_score = out["same_time_volume_ratio"].map(lambda x: scale(x, 0.6, 1.8))
    pct_score = out["pct_change"].map(lambda x: scale(x, 0.0, 3.5))
    pp_score = out["pocket_pivot_volume_pass"].map(boolish).map({True: 100.0, False: 0.0})
    out["flow_vpa_score_v2"] = (0.35 * rvol_score + 0.25 * same_score + 0.20 * pct_score + 0.20 * pp_score).round(2)

    roe = out["roe_ttm_pct"].map(lambda x: scale(x, 5, 22))
    roa = out["roa_ttm_pct"].map(lambda x: scale(x, 1, 10))
    rev_yoy = out["revenue_growth_yoy_pct"].map(lambda x: scale(x, -5, 25))
    pbt_yoy = out["pbt_growth_yoy_pct"].map(lambda x: scale(x, -5, 30))
    pbt_3y = out["pbt_growth_3y_avg_pct"].map(lambda x: scale(x, -5, 25))
    equity_3y = out["equity_growth_3y_avg_pct"].map(lambda x: scale(x, -3, 15))
    out["fundamental_growth_score_v2"] = (0.30 * roe + 0.10 * roa + 0.15 * rev_yoy + 0.20 * pbt_yoy + 0.15 * pbt_3y + 0.10 * equity_3y).round(2)

    upside = out["upside_to_base_pct"].map(lambda x: scale(x, -15, 35))
    pe_rel = (out["pe_current_calc"] / out["pe_median_8q_provider"]).replace([np.inf, -np.inf], np.nan)
    pb_rel = (out["pb_current_calc"] / out["pb_median_8q_provider"]).replace([np.inf, -np.inf], np.nan)
    pe_score = pe_rel.map(lambda x: scale(1.35 - x if not pd.isna(x) else np.nan, 0.0, 0.7))
    pb_score = pb_rel.map(lambda x: scale(1.35 - x if not pd.isna(x) else np.nan, 0.0, 0.7))
    out["valuation_score_v2"] = (0.60 * upside + 0.25 * pe_score + 0.15 * pb_score).round(2)

    out["liquidity_score_v2"] = out["vol20"].map(lambda x: scale(math.log10(max(float(x), 1)), math.log10(100_000), math.log10(5_000_000))).round(2)
    out["stockradar_score_v2"] = (
        0.35 * out["technical_score_v2"]
        + 0.20 * out["flow_vpa_score_v2"]
        + 0.20 * out["fundamental_growth_score_v2"]
        + 0.15 * out["valuation_score_v2"]
        + 0.10 * out["liquidity_score_v2"]
    ).round(2)

    stage_ok = out["stage"].isin(["STAGE_1_TO_2", "STAGE_2"])
    price_near_ma = ((out["price"] / out["ma10"] - 1).abs() <= 0.08) | ((out["price"] / out["ma50"] - 1).abs() <= 0.08)
    not_extended = (out["price"] / out["ma50"] - 1) <= 0.10
    pp = (
        out["full_scan_eligible"] & stage_ok & out["pocket_pivot_volume_pass"].map(boolish)
        & (out["pct_change"] >= 2.0) & price_near_ma & not_extended
    )
    early = (
        out["full_scan_eligible"] & stage_ok & (out["pct_change"] >= 2.0)
        & (out["distance_to_pivot_pct"] >= -1.5) & (out["distance_to_pivot_pct"] <= 2.5)
        & (out["rvol_progress_adjusted"] >= 1.10) & not_extended
    )
    confirmed = (
        out["full_scan_eligible"] & out["stage"].eq("STAGE_2") & (out["price"] >= out["pivot20"])
        & (out["pct_change"] >= 2.0) & (out["rvol_progress_adjusted"] >= 1.40) & not_extended
    )
    out["setup_internal"] = "WATCH"
    out.loc[pp, "setup_internal"] = "POCKET_PIVOT"
    out.loc[early, "setup_internal"] = "EARLY_BREAKOUT"
    out.loc[confirmed, "setup_internal"] = "CONFIRMED_BREAKOUT"
    out["action_candidate_internal"] = out["setup_internal"].map({
        "POCKET_PIVOT": "ĐẠT ĐIỂM MUA – POCKET PIVOT",
        "EARLY_BREAKOUT": "ĐẠT ĐIỂM MUA – EARLY BREAKOUT",
        "CONFIRMED_BREAKOUT": "ĐẠT ĐIỂM MUA – XÁC NHẬN",
        "WATCH": "NO_ACTION",
    })

    actionable = out["setup_internal"].ne("WATCH")
    out["buy_zone_low_internal"] = np.nan
    out["buy_zone_high_internal"] = np.nan
    pp_mask = out["setup_internal"].eq("POCKET_PIVOT")
    early_mask = out["setup_internal"].eq("EARLY_BREAKOUT")
    conf_mask = out["setup_internal"].eq("CONFIRMED_BREAKOUT")
    out.loc[pp_mask, "buy_zone_low_internal"] = out.loc[pp_mask, "price"] * 0.985
    out.loc[pp_mask, "buy_zone_high_internal"] = out.loc[pp_mask, "price"] * 1.015
    out.loc[early_mask, "buy_zone_low_internal"] = out.loc[early_mask, "pivot20"] * 0.99
    out.loc[early_mask, "buy_zone_high_internal"] = out.loc[early_mask, "pivot20"] * 1.015
    out.loc[conf_mask, "buy_zone_low_internal"] = out.loc[conf_mask, "pivot20"]
    out.loc[conf_mask, "buy_zone_high_internal"] = out.loc[conf_mask, "pivot20"] * 1.025
    mid = (out["buy_zone_low_internal"] + out["buy_zone_high_internal"]) / 2
    stop_pct = out["setup_internal"].map({"POCKET_PIVOT": 0.06, "EARLY_BREAKOUT": 0.07, "CONFIRMED_BREAKOUT": 0.06})
    out["stop_loss_internal"] = (mid * (1 - stop_pct)).where(actionable)
    risk = mid - out["stop_loss_internal"]
    out["target_near_rr2_internal"] = (mid + 2 * risk).where(actionable)
    out["downside_pct_internal"] = (((out["stop_loss_internal"] / mid) - 1) * 100).where(actionable)
    out["upside_near_pct_internal"] = (((out["target_near_rr2_internal"] / mid) - 1) * 100).where(actionable)
    out["risk_reward_near_internal"] = (out["upside_near_pct_internal"] / out["downside_pct_internal"].abs()).where(actionable)
    out["suggested_position_pct_internal"] = out["setup_internal"].map({"POCKET_PIVOT": 20, "EARLY_BREAKOUT": 25, "CONFIRMED_BREAKOUT": 50, "WATCH": 0})

    priority = {"MBB": 1, "HPG": 2, "ACB": 3}
    out["scan_priority_internal"] = out["ticker"].map(priority).fillna(999).astype(int)

    out["overall_rank_internal"] = np.nan
    eligible_idx = out.index[out["full_scan_eligible"]]
    out.loc[eligible_idx, "overall_rank_internal"] = out.loc[eligible_idx, "stockradar_score_v2"].rank(method="min", ascending=False)
    out["sector_rank_internal"] = out.groupby("sector", dropna=False)["stockradar_score_v2"].rank(method="min", ascending=False)

    rights_cols = [c for c in ["rights_publication", "rights_publication_fundamental"] if c in out.columns]
    blocked = True
    if rights_cols:
        blocked = any(out[c].astype(str).str.startswith("BLOCKED").any() for c in rights_cols)
    out["public_release_allowed"] = False if blocked else True
    out["data_role"] = "INTERNAL_RESEARCH_BOOTSTRAP"
    out["schema_version"] = SCHEMA_VERSION

    source_time_series = (
        out["source_time_ms"]
        if "source_time_ms" in out.columns
        else pd.Series(np.nan, index=out.index, dtype="float64")
    )
    source_ms = pd.to_numeric(source_time_series, errors="coerce").dropna()
    max_source_ms = int(source_ms.max()) if len(source_ms) else None
    max_source_utc = datetime.fromtimestamp(max_source_ms / 1000, tz=timezone.utc).isoformat() if max_source_ms else None

    setup_order = {"CONFIRMED_BREAKOUT": 0, "EARLY_BREAKOUT": 1, "POCKET_PIVOT": 2, "WATCH": 3}
    out["_setup_order"] = out["setup_internal"].map(setup_order)
    out = out.sort_values(["_setup_order", "scan_priority_internal", "stockradar_score_v2"], ascending=[True, True, False]).drop(columns=["_setup_order"])

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    day = args.as_of
    scanner_path = output_dir / f"stockradar_scanner_master_v2_405_{day}.csv"
    out.to_csv(scanner_path, index=False)

    website_fields = [
        "ticker", "name", "company_name_vi", "sector", "price", "pct_change", "stage", "ma10", "ma50", "ma150", "ma200", "pivot20",
        "distance_to_pivot_pct", "vol20", "rvol_progress_adjusted", "same_time_volume_ratio", "vcp_contraction_score", "pocket_pivot_volume_pass",
        "rs_percentile_3m", "rs_percentile_6m", "rs_percentile_12m", "roe_ttm_pct", "revenue_growth_yoy_pct", "pbt_growth_yoy_pct",
        "pe_current_calc", "pb_current_calc", "fair_value_bootstrap_bear", "fair_value_bootstrap_base", "fair_value_bootstrap_bull", "upside_to_base_pct",
        "stockradar_score_v2", "setup_internal", "action_candidate_internal", "buy_zone_low_internal", "buy_zone_high_internal", "stop_loss_internal",
        "target_near_rr2_internal", "risk_reward_near_internal", "suggested_position_pct_internal", "full_scan_eligible", "liquidity_pass_500k",
        "public_release_allowed", "data_role", "schema_version"
    ]
    public_rows = out[[c for c in website_fields if c in out.columns]].copy()
    items = json.loads(public_rows.replace({np.nan: None}).to_json(orient="records", force_ascii=False))

    top_overall = public_rows[out["full_scan_eligible"].values].sort_values("stockradar_score_v2", ascending=False).head(30)
    top_by_sector = {}
    for sector, group in public_rows[out["full_scan_eligible"].values].groupby("sector", dropna=False):
        key = str(sector) if pd.notna(sector) else "UNKNOWN"
        top_by_sector[key] = json.loads(group.sort_values("stockradar_score_v2", ascending=False).head(5).replace({np.nan: None}).to_json(orient="records", force_ascii=False))

    feed = {
        "schema_version": SCHEMA_VERSION,
        "as_of_date": day,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_snapshot_max_utc": max_source_utc,
        "exchange": "HOSE",
        "universe_count": len(out),
        "full_scan_eligible_count": int(out["full_scan_eligible"].sum()),
        "liquid_500k_count": int(out["liquidity_pass_500k"].sum()),
        "action_candidate_count": int(out["setup_internal"].ne("WATCH").sum()),
        "public_release_allowed": not blocked,
        "public_gate_reason": "BOOTSTRAP_SOURCE_RIGHTS_PENDING_PRODUCTION_CONTRACT" if blocked else "PASS",
        "data_role": "INTERNAL_WEBSITE_FEED_DO_NOT_PUBLISH_RAW",
        "top_overall_internal": json.loads(top_overall.replace({np.nan: None}).to_json(orient="records", force_ascii=False)),
        "top_by_sector_internal": top_by_sector,
        "items": items,
    }
    feed_path = output_dir / f"stockradar_website_feed_internal_v2_{day}.json"
    feed_path.write_text(json.dumps(feed, ensure_ascii=False, indent=2), encoding="utf-8")

    qa = {
        "schema_version": SCHEMA_VERSION,
        "as_of_date": day,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "canonical_hose_count": len(canonical),
        "coverage": coverage,
        "full_scan_eligible": int(out["full_scan_eligible"].sum()),
        "history_210d_pass": int(out["history_210d_pass"].sum()),
        "liquidity_vol20_ge_500k": int(out["liquidity_pass_500k"].sum()),
        "technical_ready": int(out["technical_ready"].sum()),
        "fundamental_ready": int(out["fundamental_ready"].sum()),
        "setup_counts": out["setup_internal"].value_counts(dropna=False).to_dict(),
        "alphanumeric_tickers": sorted([x for x in canonical if any(c.isdigit() for c in x)]),
        "alphanumeric_ticker_count": sum(any(c.isdigit() for c in x) for x in canonical),
        "source_snapshot_max_utc": max_source_utc,
        "public_gate": {"allowed": not blocked, "reason": "BOOTSTRAP_SOURCE_RIGHTS_PENDING_PRODUCTION_CONTRACT" if blocked else "PASS"},
        "assertions": {
            "universe_exact_405": len(canonical) == EXPECTED_HOSE,
            "all_inputs_cover_405": all(x["covered"] == EXPECTED_HOSE for x in coverage.values()),
            "all_tickers_valid_alphanumeric_hose_format": all(valid_ticker(x) for x in canonical),
            "website_feed_strips_scan_priority_internal": "scan_priority_internal" not in website_fields,
        }
    }
    qa_path = output_dir / f"stockradar_scanner_qa_v2_{day}.json"
    qa_path.write_text(json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8")

    return scanner_path, feed_path, qa_path, out, qa


def main():
    parser = argparse.ArgumentParser(description="Build StockRadar internal scanner/feed from normalized 405-HOSE feature tables.")
    parser.add_argument("--universe", required=True)
    parser.add_argument("--security-master", required=True)
    parser.add_argument("--technical", required=True)
    parser.add_argument("--fundamental", required=True)
    parser.add_argument("--relative-strength", required=True)
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--valuation", required=True)
    parser.add_argument("--company-profile")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--as-of", required=True)
    args = parser.parse_args()
    scanner, feed, qa, out, qa_payload = build(args)
    print(json.dumps({"scanner": str(scanner), "feed": str(feed), "qa": str(qa), "rows": len(out), "setup_counts": qa_payload["setup_counts"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
