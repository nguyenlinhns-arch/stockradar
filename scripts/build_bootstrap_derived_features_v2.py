from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np
import pandas as pd

SOURCE_ID = "KBS_PUBLIC_BOOTSTRAP_INTERNAL_ONLY"
RIGHTS = "BLOCKED_PENDING_TERMS_REVIEW"
EXPECTED_HOSE = 405

LATEST_MAP = {
    30: "revenue_growth_yoy_pct",
    31: "gross_profit_growth_yoy_pct",
    32: "pbt_growth_yoy_pct",
    37: "equity_growth_yoy_pct",
    38: "charter_capital_growth_yoy_pct",
    41: "gross_margin_pct",
    45: "roe_quarter_pct",
    47: "roa_quarter_pct",
    53: "eps_ttm",
    54: "bvps",
    55: "pe_provider_period",
    57: "pb_provider_period",
    58: "ps_provider_period",
    60: "dividend_yield_pct",
    80: "bank_ldr_pct",
    81: "bank_loan_to_assets_pct",
    11: "debt_to_equity",
    101: "cash_flow_per_share",
    103: "ev_ebitda_provider_period",
    109: "bank_cir_pct",
    115: "bank_operating_profit_growth_yoy_pct",
    117: "bank_loan_loss_provision_ratio_pct",
    122: "roe_ttm_pct",
    123: "roa_ttm_pct",
}
ROLLING_MAP = {
    55: ("pe_median_8q_provider", "median"),
    57: ("pb_median_8q_provider", "median"),
    122: ("roe_ttm_avg_8q_pct", "mean"),
    123: ("roa_ttm_avg_8q_pct", "mean"),
}
ANNUAL_MAP = {
    30: "revenue_growth_3y_avg_pct",
    32: "pbt_growth_3y_avg_pct",
    37: "equity_growth_3y_avg_pct",
}


def _read_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


def _ticker_universe(technical: pd.DataFrame) -> list[str]:
    tickers = sorted(technical["ticker"].astype(str).str.upper().unique())
    if len(tickers) != EXPECTED_HOSE:
        raise ValueError(f"technical universe must contain {EXPECTED_HOSE} tickers, got {len(tickers)}")
    return tickers


def _dedupe_cstc(df: pd.DataFrame, frequencies: tuple[str, ...]) -> pd.DataFrame:
    x = df[df["report_key"].isin(frequencies)].copy()
    if x.empty:
        return x
    # Revisions can contain duplicate rows for the same period/item. Prefer the
    # most recently updated provider row; if timestamps tie, prefer the later raw row.
    x["_rowid"] = np.arange(len(x))
    x["_updated"] = pd.to_datetime(x.get("last_update"), errors="coerce", utc=True)
    x = x.sort_values(["ticker", "period_end", "item_id", "_updated", "_rowid"], na_position="first")
    return x.drop_duplicates(["ticker", "period_end", "item_id"], keep="last").drop(columns=["_rowid", "_updated"])


def build_fundamental(financial: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    cols = ["ticker", "report_key", "item_id", "period_end", "last_update", "value", "source"]
    f = financial[[c for c in cols if c in financial.columns]].copy()
    f["ticker"] = f["ticker"].astype(str).str.upper()
    f["item_id"] = pd.to_numeric(f["item_id"], errors="coerce")
    f["period_end"] = pd.to_numeric(f["period_end"], errors="coerce")
    f["value"] = pd.to_numeric(f["value"], errors="coerce")

    q = _dedupe_cstc(f, ("CSTC_Q_P1", "CSTC_Q_P2"))
    q = q[q["item_id"].isin(set(LATEST_MAP) | set(ROLLING_MAP))]
    qp = q.pivot_table(index=["ticker", "period_end"], columns="item_id", values="value", aggfunc="last").reset_index()
    qp = qp.sort_values(["ticker", "period_end"])
    latest = qp.groupby("ticker", group_keys=False).tail(1).set_index("ticker")

    result = pd.DataFrame(index=tickers)
    result.index.name = "ticker"
    result["latest_period_end"] = latest["period_end"].reindex(tickers)
    result["source"] = SOURCE_ID
    result["fundamental_feature_status"] = np.where(result["latest_period_end"].notna(), "OK", "MISSING")
    result["rights_publication"] = RIGHTS
    for item_id, name in LATEST_MAP.items():
        result[name] = latest[item_id].reindex(tickers) if item_id in latest.columns else np.nan

    q8 = qp.groupby("ticker", group_keys=False).tail(8)
    for item_id, (name, method) in ROLLING_MAP.items():
        if item_id not in q8.columns:
            result[name] = np.nan
            continue
        grouped = q8.groupby("ticker")[item_id]
        series = grouped.median() if method == "median" else grouped.mean()
        result[name] = series.reindex(tickers)

    y = _dedupe_cstc(f, ("CSTC_Y_P1", "CSTC_Y_P2"))
    y = y[y["item_id"].isin(ANNUAL_MAP)]
    yp = y.pivot_table(index=["ticker", "period_end"], columns="item_id", values="value", aggfunc="last").reset_index().sort_values(["ticker", "period_end"])
    y3 = yp.groupby("ticker", group_keys=False).tail(3)
    for item_id, name in ANNUAL_MAP.items():
        result[name] = y3.groupby("ticker")[item_id].mean().reindex(tickers) if item_id in y3.columns else np.nan

    ordered = [
        "latest_period_end", "source", "fundamental_feature_status", "rights_publication",
        "revenue_growth_yoy_pct", "gross_profit_growth_yoy_pct", "pbt_growth_yoy_pct", "equity_growth_yoy_pct",
        "charter_capital_growth_yoy_pct", "gross_margin_pct", "roe_quarter_pct", "roa_quarter_pct", "eps_ttm", "bvps",
        "pe_provider_period", "pb_provider_period", "ps_provider_period", "dividend_yield_pct", "bank_ldr_pct",
        "bank_loan_to_assets_pct", "debt_to_equity", "cash_flow_per_share", "ev_ebitda_provider_period", "bank_cir_pct",
        "bank_operating_profit_growth_yoy_pct", "bank_loan_loss_provision_ratio_pct", "roe_ttm_pct", "roa_ttm_pct",
        "pe_median_8q_provider", "pb_median_8q_provider", "roe_ttm_avg_8q_pct", "roa_ttm_avg_8q_pct",
        "revenue_growth_3y_avg_pct", "pbt_growth_3y_avg_pct", "equity_growth_3y_avg_pct",
    ]
    return result.reset_index()[["ticker"] + ordered]


def build_relative_strength(ohlcv: pd.DataFrame, vnindex: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    h = ohlcv[["ticker", "timestamp", "close"]].copy()
    h["ticker"] = h["ticker"].astype(str).str.upper()
    h["close"] = pd.to_numeric(h["close"], errors="coerce")
    h = h.dropna(subset=["close"]).sort_values(["ticker", "timestamp"])

    v = vnindex[["timestamp", "close"]].copy()
    v["close"] = pd.to_numeric(v["close"], errors="coerce")
    v = v.dropna(subset=["close"]).sort_values("timestamp").reset_index(drop=True)

    horizons = [(63, "3m"), (126, "6m"), (252, "12m")]
    vn_returns = {}
    for bars, label in horizons:
        vn_returns[label] = (float(v.iloc[-1]["close"]) / float(v.iloc[-1 - bars]["close"]) - 1.0) if len(v) > bars else np.nan

    records = []
    for ticker in tickers:
        g = h[h["ticker"].eq(ticker)].reset_index(drop=True)
        row = {"ticker": ticker}
        for bars, label in horizons:
            ret = (float(g.iloc[-1]["close"]) / float(g.iloc[-1 - bars]["close"]) - 1.0) if len(g) > bars else np.nan
            row[f"return_{label}"] = ret
            row[f"rel_return_vs_vnindex_{label}"] = ret - vn_returns[label] if pd.notna(ret) and pd.notna(vn_returns[label]) else np.nan
        records.append(row)
    result = pd.DataFrame(records)
    for _, label in horizons:
        result[f"rs_percentile_{label}"] = result[f"return_{label}"].rank(pct=True) * 100.0
    return result


def build_valuation(fundamental: pd.DataFrame, technical: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "ticker", "eps_ttm", "bvps", "pe_median_8q_provider", "pb_median_8q_provider",
        "ev_ebitda_provider_period", "dividend_yield_pct", "roe_ttm_pct", "revenue_growth_3y_avg_pct", "pbt_growth_3y_avg_pct"
    ]
    v = fundamental[cols].merge(technical[["ticker", "price"]], on="ticker", how="left")
    v["pe_current_calc"] = np.where(v["eps_ttm"] > 0, v["price"] / v["eps_ttm"], np.nan)
    v["pb_current_calc"] = np.where(v["bvps"] > 0, v["price"] / v["bvps"], np.nan)
    pe_target = v["pe_median_8q_provider"].where(v["pe_median_8q_provider"] > 0).clip(lower=3.0, upper=35.0)
    pb_target = v["pb_median_8q_provider"].where(v["pb_median_8q_provider"] > 0).clip(lower=0.3, upper=6.0)
    v["fv_pe_bootstrap"] = np.where((v["eps_ttm"] > 0) & pe_target.notna(), v["eps_ttm"] * pe_target, np.nan)
    v["fv_pb_bootstrap"] = np.where((v["bvps"] > 0) & pb_target.notna(), v["bvps"] * pb_target, np.nan)
    both = v[["fv_pe_bootstrap", "fv_pb_bootstrap"]].notna().all(axis=1)
    only_pe = v["fv_pe_bootstrap"].notna() & v["fv_pb_bootstrap"].isna()
    only_pb = v["fv_pb_bootstrap"].notna() & v["fv_pe_bootstrap"].isna()
    base = pd.Series(np.nan, index=v.index, dtype=float)
    base.loc[both] = 0.65 * v.loc[both, "fv_pe_bootstrap"] + 0.35 * v.loc[both, "fv_pb_bootstrap"]
    base.loc[only_pe] = v.loc[only_pe, "fv_pe_bootstrap"]
    base.loc[only_pb] = v.loc[only_pb, "fv_pb_bootstrap"]
    v["fair_value_bootstrap_base"] = base
    v["fair_value_bootstrap_bear"] = base * 0.85
    v["fair_value_bootstrap_bull"] = base * 1.15
    v["upside_to_base_pct"] = np.where(v["price"] > 0, (base / v["price"] - 1.0) * 100.0, np.nan)
    v["mos_to_base_pct"] = np.where(base > 0, (1.0 - v["price"] / base) * 100.0, np.nan)
    v["valuation_model_status"] = np.where(base.notna(), "BOOTSTRAP_INTERNAL_ONLY", "INSUFFICIENT_DATA")
    for c in ["pe_current_calc", "pb_current_calc", "revenue_growth_3y_avg_pct", "pbt_growth_3y_avg_pct", "fv_pe_bootstrap", "fv_pb_bootstrap", "fair_value_bootstrap_bear", "fair_value_bootstrap_base", "fair_value_bootstrap_bull", "upside_to_base_pct", "mos_to_base_pct"]:
        v[c] = pd.to_numeric(v[c], errors="coerce").round(4)
    ordered = [
        "ticker", "price", "eps_ttm", "bvps", "pe_current_calc", "pb_current_calc", "pe_median_8q_provider", "pb_median_8q_provider",
        "ev_ebitda_provider_period", "dividend_yield_pct", "roe_ttm_pct", "revenue_growth_3y_avg_pct", "pbt_growth_3y_avg_pct",
        "fv_pe_bootstrap", "fv_pb_bootstrap", "fair_value_bootstrap_bear", "fair_value_bootstrap_base", "fair_value_bootstrap_bull",
        "upside_to_base_pct", "mos_to_base_pct", "valuation_model_status"
    ]
    return v[ordered]


def main() -> None:
    parser = argparse.ArgumentParser(description="Derive StockRadar internal fundamental, RS and bootstrap valuation features from normalized artifacts.")
    parser.add_argument("--financial-statements", required=True)
    parser.add_argument("--ohlcv", required=True)
    parser.add_argument("--vnindex-daily", required=True)
    parser.add_argument("--technical", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    financial = _read_csv(args.financial_statements)
    ohlcv = _read_csv(args.ohlcv)
    vnindex = _read_csv(args.vnindex_daily)
    technical = _read_csv(args.technical)
    technical["ticker"] = technical["ticker"].astype(str).str.upper()
    tickers = _ticker_universe(technical)

    fundamental = build_fundamental(financial, tickers)
    rs = build_relative_strength(ohlcv, vnindex, tickers)
    valuation = build_valuation(fundamental, technical)

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    fundamental.to_csv(out / "fundamental_features_bootstrap.csv", index=False)
    rs.to_csv(out / "relative_strength_bootstrap.csv", index=False)
    valuation.to_csv(out / "valuation_bootstrap.csv", index=False)
    print(f"derived features: fundamental={len(fundamental)}, rs={len(rs)}, valuation={len(valuation)}")


if __name__ == "__main__":
    main()
