from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re

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
    "LISTING_STATUS": 70,
    "GOVERNANCE": 58,
    "OTHER": 40,
}
KEYWORDS = {
    "EARNINGS": ("kết quả kinh doanh", "báo cáo tài chính", "bctc", "lợi nhuận", "doanh thu", "lãi ròng", "ước lợi nhuận", "kqkd"),
    "CAPACITY": ("nhà máy", "công suất", "khởi công", "vận hành", "mở rộng", "dây chuyền"),
    "MA_CONSOLIDATION": ("sáp nhập", "mua lại", "m&a", "thoái vốn", "chuyển nhượng", "thâu tóm"),
    "MAJOR_CONTRACT": ("trúng thầu", "hợp đồng", "đơn hàng", "gói thầu"),
    "POLICY_INDUSTRY": ("chính sách", "nghị định", "thuế", "hạn ngạch", "quota", "giá bán", "điều chỉnh giá"),
    "INSIDER": ("người nội bộ", "người có liên quan", "giao dịch cổ phiếu", "giao dịch quyền mua"),
    "CAPITAL_ACTION": ("cổ tức", "phát hành", "chào bán", "quyền mua", "esop", "chia cổ phiếu", "thưởng cổ phiếu", "ngày đăng ký cuối cùng", "ngày đkcc"),
    "LISTING_STATUS": ("hủy niêm yết", "tạm ngừng giao dịch", "đình chỉ giao dịch", "thay đổi niêm yết", "thay đổi đăng ký niêm yết", "niêm yết bổ sung", "tình trạng chứng khoán"),
    "GOVERNANCE": ("bổ nhiệm", "miễn nhiệm", "chủ tịch", "tổng giám đốc", "hđqt", "đhđcđ", "đại hội đồng cổ đông"),
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
    return " ".join(str(item.get(k)) for k in TITLE_KEYS if item.get(k)).strip()


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


def title_key(text: str) -> str:
    return re.sub(r"[^0-9a-zA-ZÀ-ỹ]+", " ", str(text or "").casefold()).strip()


def flatten_recall(df: pd.DataFrame, insider: bool, as_of: pd.Timestamp) -> list[dict]:
    rows = []
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
                "title_key": title_key(text),
                "source_kind": "KBS_INSIDER_RECALL" if insider else "KBS_NEWS_RECALL",
                "official_verified": False,
            })
    return rows


def flatten_official(path: str | None, as_of: pd.Timestamp) -> list[dict]:
    if not path or not Path(path).exists():
        return []
    df = pd.read_csv(path)
    if df.empty or "ticker" not in df.columns:
        return []
    rows = []
    for _, record in df.iterrows():
        ticker = str(record.get("ticker") or "").strip().upper()
        if not ticker:
            continue
        text = str(record.get("title") or "").strip()
        dt = pd.to_datetime(record.get("updated_at"), errors="coerce", utc=True)
        if pd.notna(dt):
            dt = dt.tz_convert(None)
        age = (as_of - dt.normalize()).days if pd.notna(dt) else np.nan
        category = str(record.get("category") or "").strip().upper()
        if category not in MATERIALITY:
            category = classify(text)
        rows.append({
            "ticker": ticker,
            "event_time": dt,
            "age_days": age,
            "category": category,
            "materiality": MATERIALITY[category],
            "recency_weight": recency_weight(age),
            "weighted_materiality": MATERIALITY[category] * recency_weight(age),
            "title": text[:500],
            "title_key": title_key(text),
            "source_kind": "HOSE_OFFICIAL",
            "official_verified": True,
        })
    return rows


def read_manifest(path: str | None) -> dict:
    if not path or not Path(path).exists():
        return {}
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return {}


def build(args) -> None:
    news = pd.read_csv(args.news)
    insider = pd.read_csv(args.insider)
    universe = pd.read_csv(args.universe)
    as_of = pd.Timestamp(args.as_of)
    tickers = sorted(set(universe["ticker"].astype(str).str.strip().str.upper()))
    if len(tickers) != EXPECTED_HOSE:
        raise ValueError(f"canonical HOSE must be {EXPECTED_HOSE}, got {len(tickers)}")

    recall_rows = flatten_recall(news, False, as_of) + flatten_recall(insider, True, as_of)
    official_rows = flatten_official(args.official_disclosures, as_of)
    events = pd.DataFrame(recall_rows + official_rows)
    if not events.empty:
        events = events[events["ticker"].isin(tickers)].copy()
        # Exact normalized title duplicates are retained once, favoring official HOSE evidence.
        events["official_rank"] = events["official_verified"].astype(int)
        events = events.sort_values(["official_rank", "event_time"], ascending=[False, False])
        events = events.drop_duplicates(subset=["ticker", "title_key"], keep="first").drop(columns=["official_rank"])

    official_manifest = read_manifest(args.official_manifest)
    official_source_ready = bool(official_manifest.get("source_ready_internal") is True) if official_manifest else bool(official_rows)

    output_rows = []
    for ticker in tickers:
        g = events[events["ticker"].eq(ticker)].copy() if not events.empty else pd.DataFrame()
        recent90 = g[g["age_days"].between(0, 90, inclusive="both")] if not g.empty else g
        recent30 = g[g["age_days"].between(0, 30, inclusive="both")] if not g.empty else g
        official90 = recent90[recent90["official_verified"].eq(True)] if not recent90.empty else recent90
        official30 = recent30[recent30["official_verified"].eq(True)] if not recent30.empty else recent30
        recall90 = recent90[recent90["official_verified"].eq(False)] if not recent90.empty else recent90

        dated = int(g["event_time"].notna().sum()) if not g.empty else 0
        total = len(g)
        dated_ratio = dated / total if total else 0.0
        categories = int(recent90["category"].nunique()) if not recent90.empty else 0
        depth = min(1.0, len(recent90) / 4.0)
        category_conf = min(1.0, categories / 2.0)
        base_confidence = round(100 * (0.45 * dated_ratio + 0.35 * depth + 0.20 * category_conf), 2)
        evidence_boost = 15.0 if len(official90) > 0 else 0.0
        confidence_v3 = round(min(100.0, base_confidence + evidence_boost), 2)
        ready_v2 = base_confidence >= 65 and len(recent90) >= 2

        score = np.nan
        top_category = None
        latest_title = None
        latest_time = pd.NaT
        latest_official_title = None
        latest_official_time = pd.NaT
        if not recent90.empty:
            top = recent90.sort_values(["weighted_materiality", "event_time"], ascending=[False, False]).iloc[0]
            top_category = top["category"]
            score = round(float(recent90["weighted_materiality"].nlargest(min(3, len(recent90))).mean()), 2)
            latest = recent90.sort_values("event_time", ascending=False).iloc[0]
            latest_title = latest["title"]
            latest_time = latest["event_time"]
        if not official90.empty:
            latest_official = official90.sort_values("event_time", ascending=False).iloc[0]
            latest_official_title = latest_official["title"]
            latest_official_time = latest_official["event_time"]

        if len(official90) > 0:
            verification_state = "OFFICIAL_HOSE_RECENT_VERIFIED"
        elif len(recall90) > 0:
            verification_state = "RECALL_ONLY_UNVERIFIED"
        else:
            verification_state = "NO_RECENT_CATALYST_EVIDENCE"

        output_rows.append({
            "ticker": ticker,
            "news_insider_items_total": total,
            "items_90d": len(recent90),
            "items_30d": len(recent30),
            "dated_ratio": round(dated_ratio, 4),
            "category_count_90d": categories,
            "catalyst_confidence_v2": base_confidence,
            "catalyst_data_ready_v2": ready_v2,
            "catalyst_score_v2": score if ready_v2 else np.nan,
            "top_catalyst_category_v2": top_category,
            "latest_catalyst_time_v2": latest_time,
            "latest_catalyst_title_v2": latest_title,
            "catalyst_alpha_weight_allowed_v2": False,
            "official_items_90d_v3": int(len(official90)),
            "official_items_30d_v3": int(len(official30)),
            "recall_only_items_90d_v3": int(len(recall90)),
            "latest_official_catalyst_time_v3": latest_official_time,
            "latest_official_catalyst_title_v3": latest_official_title,
            "catalyst_confidence_v3": confidence_v3,
            "catalyst_official_verified_v3": bool(len(official90) > 0),
            "catalyst_verification_state_v3": verification_state,
            "official_hose_source_ready_v3": official_source_ready,
            "catalyst_alpha_weight_allowed_v3": False,
        })

    out = pd.DataFrame(output_rows)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output, index=False, encoding="utf-8-sig")
    manifest = {
        "schema_version": "STOCKRADAR_CATALYST_V3",
        "canonical_hose": EXPECTED_HOSE,
        "raw_distinct_event_count": int(len(events)),
        "recall_rows_input": int(len(recall_rows)),
        "official_rows_input": int(len(official_rows)),
        "official_hose_source_ready": official_source_ready,
        "tickers_with_90d_items": int((out["items_90d"] > 0).sum()),
        "tickers_with_official_90d_items": int((out["official_items_90d_v3"] > 0).sum()),
        "catalyst_data_ready_v2_compatible": int(out["catalyst_data_ready_v2"].sum()),
        "catalyst_alpha_weight_allowed": False,
        "policy": "KBS is recall-only; official HOSE RSS is verification/context. Official evidence may raise evidence confidence but never enables catalyst alpha by itself.",
        "publication_allowed": False,
    }
    Path(args.manifest).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--news", required=True)
    p.add_argument("--insider", required=True)
    p.add_argument("--official-disclosures")
    p.add_argument("--official-manifest")
    p.add_argument("--universe", required=True)
    p.add_argument("--as-of", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--manifest", required=True)
    build(p.parse_args())


if __name__ == "__main__":
    main()
