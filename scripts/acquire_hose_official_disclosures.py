#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from html import unescape
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import pandas as pd
import requests

FEED_URL = "https://api.hsx.vn/n/api/v1/News/NewsByCateFeed/21"
SOURCE_ID = "HOSE_OFFICIAL_LISTED_COMPANY_NEWS_RSS"
HEADERS = {
    "User-Agent": "StockRadar-Internal-Research/1.0",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.7",
}
A10 = "{http://www.w3.org/2005/Atom}updated"
KEYWORDS = {
    "EARNINGS": ("kết quả kinh doanh", "báo cáo tài chính", "bctc", "lợi nhuận", "doanh thu"),
    "CAPACITY": ("nhà máy", "công suất", "khởi công", "vận hành", "mở rộng", "dây chuyền"),
    "MA_CONSOLIDATION": ("sáp nhập", "mua lại", "m&a", "thoái vốn", "chuyển nhượng", "thâu tóm"),
    "MAJOR_CONTRACT": ("trúng thầu", "hợp đồng", "đơn hàng", "gói thầu"),
    "POLICY_INDUSTRY": ("chính sách", "nghị định", "thuế", "hạn ngạch", "quota", "điều chỉnh giá"),
    "CAPITAL_ACTION": ("cổ tức", "phát hành", "quyền mua", "esop", "chia cổ phiếu", "thưởng cổ phiếu", "ngày đăng ký cuối cùng"),
    "GOVERNANCE": ("bổ nhiệm", "miễn nhiệm", "chủ tịch", "tổng giám đốc", "hđqt", "đhđcđ", "đại hội đồng cổ đông"),
    "LISTING_STATUS": ("hủy niêm yết", "tạm ngừng giao dịch", "đình chỉ giao dịch", "thay đổi niêm yết", "niêm yết bổ sung"),
}


def clean_html(value: str | None) -> str:
    text = unescape(value or "")
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_ticker(title: str) -> str:
    m = re.match(r"^\s*([A-Z0-9]{3})(?=\s*[:\-–—])", title.upper())
    if not m:
        return ""
    ticker = m.group(1)
    return ticker if any(ch.isalpha() for ch in ticker) else ""


def classify(title: str) -> str:
    low = title.casefold()
    for category, terms in KEYWORDS.items():
        if any(term in low for term in terms):
            return category
    return "OTHER"


def parse_feed(xml_text: str) -> list[dict[str, object]]:
    root = ET.fromstring(xml_text)
    rows = []
    for item in root.findall("./channel/item"):
        guid = clean_html(item.findtext("guid"))
        link = clean_html(item.findtext("link"))
        title = clean_html(item.findtext("title"))
        description = clean_html(item.findtext("description"))
        updated_raw = clean_html(item.findtext(A10) or item.findtext("updated") or item.findtext("pubDate"))
        updated = pd.to_datetime(updated_raw, errors="coerce", utc=True)
        rows.append({
            "guid": guid,
            "ticker": extract_ticker(title),
            "updated_at": updated.isoformat() if pd.notna(updated) else "",
            "title": title,
            "description": description,
            "link": link,
            "category": classify(title),
            "source_id": SOURCE_ID,
            "official_verified": True,
            "raw_publication_allowed": False,
            "derived_alpha_weight_allowed": False,
        })
    return rows


def read_history(path: str | None) -> pd.DataFrame:
    if not path:
        return pd.DataFrame()
    p = Path(path)
    if not p.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(p)
    except Exception:
        return pd.DataFrame()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--history")
    p.add_argument("--output-dir", default="artifacts/hose-official-disclosures")
    args = p.parse_args()

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    response = requests.get(FEED_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()
    rows = parse_feed(response.text)
    current = pd.DataFrame(rows)
    if current.empty:
        raise SystemExit("HOSE listed-company RSS returned zero parseable items")

    history = read_history(args.history)
    combined = pd.concat([history, current], ignore_index=True, sort=False) if not history.empty else current.copy()
    combined["guid"] = combined["guid"].fillna("").astype(str)
    combined["updated_at"] = combined["updated_at"].fillna("").astype(str)
    combined = combined.drop_duplicates(subset=["guid"], keep="last")
    combined["updated_dt"] = pd.to_datetime(combined["updated_at"], errors="coerce", utc=True)
    combined = combined.sort_values(["updated_dt", "guid"], ascending=[False, False]).drop(columns=["updated_dt"])

    current.to_csv(out / "hose_official_disclosures_current.csv", index=False, encoding="utf-8-sig")
    combined.to_csv(out / "hose_official_disclosures_history.csv", index=False, encoding="utf-8-sig")

    dated = pd.to_datetime(current["updated_at"], errors="coerce", utc=True)
    manifest = {
        "schema_version": "STOCKRADAR_HOSE_OFFICIAL_DISCLOSURES_V1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_id": SOURCE_ID,
        "source_url": FEED_URL,
        "http_status": response.status_code,
        "content_type": response.headers.get("content-type", ""),
        "feed_items_observed": int(len(current)),
        "feed_items_with_ticker": int(current["ticker"].fillna("").ne("").sum()),
        "feed_items_with_timestamp": int(dated.notna().sum()),
        "history_rows": int(len(combined)),
        "history_unique_tickers": int(combined["ticker"].fillna("").replace("", pd.NA).nunique()),
        "latest_item_at": dated.max().isoformat() if dated.notna().any() else None,
        "earliest_item_at": dated.min().isoformat() if dated.notna().any() else None,
        "source_ready_internal": bool(len(current) > 0 and dated.notna().all()),
        "official_verification_layer": True,
        "catalyst_alpha_weight_allowed": False,
        "publication_allowed": False,
        "note": "Official HOSE RSS metadata is an internal verification/context input. KBS remains recall-only. Public redistribution and catalyst alpha remain independently fail-closed.",
    }
    (out / "hose_official_disclosures_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))


if __name__ == "__main__":
    main()
