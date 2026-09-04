from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

EXPECTED_HOSE = 405
MATERIALITY = {
    "EARNINGS": 85,
    "CAPACITY": 82,
    "MA_CONSOLIDATION": 88,
    "MAJOR_CONTRACT": 80,
    "POLICY_INDUSTRY": 72,
    "CAPITAL_ACTION": 65,
    "INSIDER": 62,
    "GOVERNANCE": 58,
    "OTHER": 40,
}
KEYWORDS = {
    "EARNINGS": ("kết quả kinh doanh", "lợi nhuận", "doanh thu", "lãi ròng", "ước lợi nhuận", "kqkd"),
    "CAPACITY": ("nhà máy", "công suất", "khởi công", "vận hành", "mở rộng", "dây chuyền"),
    "MA_CONSOLIDATION": ("sáp nhập", "mua lại", "m&a", "thoái vốn", "chuyển nhượng", "thâu tóm"),
    "MAJOR_CONTRACT": ("trúng thầu", "hợp đồng", "đơn hàng", "gói thầu"),
    "POLICY_INDUSTRY": ("chính sách", "nghị định", "thuế", "hạn ngạch", "quota", "giá bán", "điều chỉnh giá"),
    "CAPITAL_ACTION": ("cổ tức", "phát hành", "quyền mua", "esop", "chia cổ phiếu", "thưởng cổ phiếu"),
    "GOVERNANCE": ("bổ nhiệm", "miễn nhiệm", "chủ tịch", "tổng giám đốc", "hđqt"),
}
DATE_KEYS = ("PublishTime", "Date", "Time", "CreatedDate", "TradingDate")
TITLE_KEYS = ("Title", "title", "Subject", "subject", "Content", "content")


def parse_payload(value):
    try:
        obj = json.loads(value) if isinstance(value, str) else value
    except Exception:
        return []
    if isinstance(obj, list):
        return [x for x in obj if isinstance(x, dict)]
    if isinstance(obj, dict):
        return [obj]
    return []


def text_of(item: dict) -> str:
    parts = []
    for key in TITLE_KEYS:
        value = item.get(key)
        if value:
            parts.append(str(value))
    return " ".join(parts).strip()


def date_of(item: dict):
    for key in DATE_KEYS:
        value = item.get(key)
        if value not in (None, ""):
            dt = pd.to_datetime(value, errors="coerce", utc=True)
            if pd.notna(dt):
                return dt.tz_convert(None)
    return pd.NaT


def classify(text: str, insider: bool = False) -> str:
    if insider:
        return "INSIDER"
    low = text.casefold()
    for category, terms in KEYWORDS.items():
        if any(term in low for term in terms):
            return category
    return "OTHER"


def recency_weight(age_days: float) -> float:
    if pd.isna(age_days) or age_days < 0:
        return 0.0
    return math.exp(-float(age_days) / 45.0)


def flatten(df: pd.DataFrame, insider: bool, as_of: pd.Timestamp) -> list[dict]:
    rows: list[dict] = []
    for _, record in df.iterrows():
        ticker = str(record.get("ticker") or "").strip().upper()
        for item in parse_payload(record.get("payload")):
            text = text_of(item)
            dt = date_of(item)
            age = (as_of - dt.normalize()).days if pd.notna(dt) else np.nan
            category = classify(text, insider=insider)
            rows.append({
                "ticker": ticker,
                "event_time": dt,
                "age_days": age,
                "category": category,
                "materiality": MATERIALITY[category],
                "recency_weight": recency_weight(age),
                "weighted_materiality": MATERIALITY[category] * recency_weight(age),
                "title": text[:500],
                "source_kind": "INSIDER" if insider else "NEWS",
            })
    return rows


def build(args) -> None:
    news = pd.read_csv(args.news)
    insider = pd.read_csv(args.insider)
    universe = pd.read_csv(args.universe)
    as_of = pd.Timestamp(args.as_of)
    tickers = sorted(set(universe["ticker"].astype(str).str.strip().str.upper()))
    if len(tickers) != EXPECTED_HOSE:
        raise ValueError(f"canonical HOSE must be {EXPECTED_HOSE}, got {len(tickers)}")

    events = pd.DataFrame(flatten(news, False, as_of) + flatten(insider, True, as_of))
    output_rows = []
    for ticker in tickers:
        g = events[events["ticker"].eq(ticker)].copy() if not events.empty else pd.DataFrame()
        recent90 = g[g["age_days"].between(0, 90, inclusive="both")] if not g.empty else g
        recent30 = g[g["age_days"].between(0, 30, inclusive="both")] if not g.empty else g
        dated = int(g["event_time"].notna().sum()) if not g.empty else 0
        total = len(g)
        dated_ratio = dated / total if total else 0.0
        categories = int(recent90["category"].nunique()) if not recent90.empty else 0
        depth = min(1.0, len(recent90) / 4.0)
        category_conf = min(1.0, categories / 2.0)
        confidence = round(100 * (0.45 * dated_ratio + 0.35 * depth + 0.20 * category_conf), 2)
        ready = confidence >= 65 and len(recent90) >= 2
        score = np.nan
        top_category = None
        latest_title = None
        latest_time = pd.NaT
        if not recent90.empty:
            top = recent90.sort_values(["weighted_materiality", "event_time"], ascending=[False, False]).iloc[0]
            top_category = top["category"]
            score = round(float(recent90["weighted_materiality"].nlargest(min(3, len(recent90))).mean()), 2)
            latest = recent90.sort_values("event_time", ascending=False).iloc[0]
            latest_title = latest["title"]
            latest_time = latest["event_time"]
        output_rows.append({
            "ticker": ticker,
            "news_insider_items_total": total,
            "items_90d": len(recent90),
            "items_30d": len(recent30),
            "dated_ratio": round(dated_ratio, 4),
            "category_count_90d": categories,
            "catalyst_confidence_v2": confidence,
            "catalyst_data_ready_v2": ready,
            "catalyst_score_v2": score if ready else np.nan,
            "top_catalyst_category_v2": top_category,
            "latest_catalyst_time_v2": latest_time,
            "latest_catalyst_title_v2": latest_title,
            "catalyst_alpha_weight_allowed_v2": False,
        })

    out = pd.DataFrame(output_rows)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output, index=False, encoding="utf-8-sig")
    manifest = {
        "schema_version": "STOCKRADAR_CATALYST_V2",
        "canonical_hose": EXPECTED_HOSE,
        "raw_event_count": int(len(events)),
        "tickers_with_90d_items": int((out["items_90d"] > 0).sum()),
        "catalyst_data_ready": int(out["catalyst_data_ready_v2"].sum()),
        "catalyst_alpha_weight_allowed": False,
        "policy": "Materiality x recency with evidence-depth confidence. Article count alone is never an alpha score.",
        "publication_allowed": False,
    }
    Path(args.manifest).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--news", required=True)
    p.add_argument("--insider", required=True)
    p.add_argument("--universe", required=True)
    p.add_argument("--as-of", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--manifest", required=True)
    build(p.parse_args())


if __name__ == "__main__":
    main()
