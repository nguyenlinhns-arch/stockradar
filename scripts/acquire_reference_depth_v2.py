#!/usr/bin/env python3
from __future__ import annotations

import concurrent.futures as cf
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from typing import Any

import pandas as pd
import requests

BASE = "https://kbbuddywts.kbsec.com.vn/iis-server/investment"
HEADERS = {"Accept": "application/json", "Accept-Language": "vi,en;q=0.8", "User-Agent": "StockRadar-Internal-Research/2.0", "x-lang": "vi"}
SOURCE_ID = "KBS_PUBLIC_BOOTSTRAP_INTERNAL_ONLY"
TIMEOUT = 30
MAX_PAGES = 10
PAGE_SIZE = 20


def clean_symbol(value: Any) -> str:
    s = str(value or "").strip().upper()
    return s if len(s) == 3 and s.isascii() and s.isalnum() and any(ch.isalpha() for ch in s) else ""


def get_json(session: requests.Session, path: str, params=None, retries=4):
    url = f"{BASE}{path}"
    last = None
    for attempt in range(retries):
        try:
            r = session.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            last = exc
            time.sleep(min(8, 0.8 * (2**attempt)))
    raise RuntimeError(f"GET failed {url}: {last}")


def as_items(payload):
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("items", "data", "Data", "Content", "news", "events", "result", "Result"):
        value = payload.get(key)
        if isinstance(value, list):
            return [x for x in value if isinstance(x, dict)]
    # Some KBS endpoints return a single article/event object directly.
    if any(k in payload for k in ("Title", "ArticleID", "EventID", "PublishTime")):
        return [payload]
    return []


def identity(item):
    for key in ("ArticleID", "EventID", "ID", "Url", "URL", "Title"):
        value = item.get(key)
        if value not in (None, ""):
            return f"{key}:{value}"
    return json.dumps(item, ensure_ascii=False, sort_keys=True, default=str)


def fetch_pages(session, path, language=1):
    collected = []
    seen = set()
    empty_streak = 0
    for page in range(1, MAX_PAGES + 1):
        payload = get_json(session, path, {"l": language, "p": page, "s": PAGE_SIZE})
        items = as_items(payload)
        new_count = 0
        for item in items:
            key = identity(item)
            if key not in seen:
                seen.add(key)
                collected.append(item)
                new_count += 1
        if not items or new_count == 0:
            empty_streak += 1
        else:
            empty_streak = 0
        if empty_streak >= 2:
            break
        if len(items) < PAGE_SIZE and page > 1:
            break
    return collected


def fetch_universe():
    with requests.Session() as s:
        listing = get_json(s, "/stock/search/data")
    tickers = []
    for item in listing if isinstance(listing, list) else []:
        ticker = clean_symbol(item.get("symbol"))
        if ticker and str(item.get("exchange") or "").upper() == "HOSE" and str(item.get("type") or "stock").lower() in {"stock", "equity", ""}:
            tickers.append(ticker)
    return sorted(set(tickers))


def fetch_one(ticker):
    try:
        with requests.Session() as s:
            news = fetch_pages(s, f"/stockinfo/news/{ticker}")
            insider = fetch_pages(s, f"/stockinfo/news/internal-trading/{ticker}")
        return ticker, news, insider, None
    except Exception as exc:
        return ticker, [], [], str(exc)


def event_candidates(ticker, articles):
    keywords = (
        "cổ tức", "ngày đăng ký cuối cùng", "giao dịch không hưởng quyền", "phát hành", "quyền mua",
        "esop", "chia cổ phiếu", "thưởng cổ phiếu", "tạm ngừng giao dịch", "hủy niêm yết", "đăng ký giao dịch bổ sung"
    )
    rows = []
    for item in articles:
        title = str(item.get("Title") or "")
        if any(k in title.lower() for k in keywords):
            rows.append({
                "ticker": ticker,
                "title": title,
                "publish_time": item.get("PublishTime"),
                "article_id": item.get("ArticleID"),
                "url": item.get("URL") or item.get("Url"),
                "source": SOURCE_ID,
                "verification_state": "NEWS_DERIVED_UNVERIFIED",
            })
    return rows


def main():
    out = Path("artifacts/reference-depth-v2")
    out.mkdir(parents=True, exist_ok=True)
    tickers = fetch_universe()
    if len(tickers) < 405:
        raise RuntimeError(f"HOSE universe unexpectedly small: {len(tickers)}")

    news_rows, insider_rows, event_rows, errors = [], [], [], []
    with cf.ThreadPoolExecutor(max_workers=10) as ex:
        futures = [ex.submit(fetch_one, t) for t in tickers]
        for fut in cf.as_completed(futures):
            ticker, news, insider, err = fut.result()
            if err:
                errors.append({"ticker": ticker, "error": err})
            news_rows.append({"ticker": ticker, "source": SOURCE_ID, "item_count": len(news), "payload": json.dumps(news, ensure_ascii=False, separators=(",", ":"), default=str)})
            insider_rows.append({"ticker": ticker, "source": SOURCE_ID, "item_count": len(insider), "payload": json.dumps(insider, ensure_ascii=False, separators=(",", ":"), default=str)})
            event_rows.extend(event_candidates(ticker, news))

    pd.DataFrame(news_rows).sort_values("ticker").to_csv(out / "company_news_depth_v2.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(insider_rows).sort_values("ticker").to_csv(out / "insider_trading_depth_v2.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(event_rows).to_csv(out / "corporate_action_candidates_from_news_v2.csv", index=False, encoding="utf-8-sig")
    coverage = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": SOURCE_ID,
        "universe": len(tickers),
        "news_tickers": len(news_rows),
        "news_items": sum(r["item_count"] for r in news_rows),
        "insider_tickers": len(insider_rows),
        "insider_items": sum(r["item_count"] for r in insider_rows),
        "news_derived_event_candidates": len(event_rows),
        "event_candidates_are_verified": False,
        "publication_allowed": False,
        "errors": errors,
    }
    (out / "reference_depth_v2_coverage.json").write_text(json.dumps(coverage, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
