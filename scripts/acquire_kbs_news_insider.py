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
HEADERS = {
    "Accept": "application/json",
    "Accept-Language": "vi,en;q=0.8",
    "User-Agent": "StockRadar-Internal-Research/1.0",
    "x-lang": "vi",
}
SOURCE_ID = "KBS_PUBLIC_BOOTSTRAP_INTERNAL_ONLY"
TIMEOUT = 30


def clean_symbol(value: Any) -> str:
    s = str(value or "").strip().upper()
    return s if len(s) == 3 and s.isascii() and s.isalnum() and any(ch.isalpha() for ch in s) else ""


def get_json(session: requests.Session, path: str, params: dict[str, Any] | None = None, retries: int = 4) -> Any:
    last: Exception | None = None
    url = f"{BASE}{path}"
    for attempt in range(retries):
        try:
            r = session.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            last = exc
            time.sleep(min(8, 0.8 * (2 ** attempt)))
    raise RuntimeError(f"GET failed {url}: {last}")


def payload_ok(payload: Any) -> bool:
    if payload is None:
        return False
    if isinstance(payload, dict) and str(payload.get("st") or "").lower() == "err":
        return False
    return isinstance(payload, (dict, list))


def fetch_universe() -> list[str]:
    with requests.Session() as s:
        listing = get_json(s, "/stock/search/data")
    rows = []
    for item in listing if isinstance(listing, list) else []:
        ticker = clean_symbol(item.get("symbol"))
        ex = str(item.get("exchange") or "").upper()
        typ = str(item.get("type") or "stock").lower()
        if ticker and ex == "HOSE" and typ in {"stock", "equity", ""}:
            rows.append(ticker)
    return sorted(set(rows))


def fetch_one(ticker: str) -> tuple[str, Any, Any, str | None]:
    try:
        with requests.Session() as s:
            news = get_json(s, f"/stockinfo/news/{ticker}", {"l": 1, "p": 1, "s": 20})
            insider = get_json(s, f"/stockinfo/news/internal-trading/{ticker}", {"l": 1, "p": 1, "s": 20})
        return ticker, news, insider, None
    except Exception as exc:
        return ticker, None, None, str(exc)


def main() -> None:
    out = Path("artifacts/reference")
    out.mkdir(parents=True, exist_ok=True)
    tickers = fetch_universe()
    if len(tickers) < 405:
        raise RuntimeError(f"HOSE universe unexpectedly small: {len(tickers)}; expected at least 405")

    news_rows: list[dict[str, str]] = []
    insider_rows: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []
    with cf.ThreadPoolExecutor(max_workers=10) as ex:
        futures = [ex.submit(fetch_one, t) for t in tickers]
        for fut in cf.as_completed(futures):
            ticker, news, insider, err = fut.result()
            if err:
                errors.append({"ticker": ticker, "dataset": "request", "error": err})
                continue
            if payload_ok(news):
                news_rows.append({"ticker": ticker, "source": SOURCE_ID, "payload": json.dumps(news, ensure_ascii=False, separators=(",", ":"), default=str)})
            else:
                errors.append({"ticker": ticker, "dataset": "news", "error": "invalid/error payload"})
            if payload_ok(insider):
                insider_rows.append({"ticker": ticker, "source": SOURCE_ID, "payload": json.dumps(insider, ensure_ascii=False, separators=(",", ":"), default=str)})
            else:
                errors.append({"ticker": ticker, "dataset": "insider", "error": "invalid/error payload"})

    pd.DataFrame(news_rows).sort_values("ticker").to_csv(out / "company_news_raw.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(insider_rows).sort_values("ticker").to_csv(out / "insider_trading_raw.csv", index=False, encoding="utf-8-sig")
    coverage = {
        "as_of": datetime.now(timezone.utc).isoformat(),
        "source": SOURCE_ID,
        "public_rights": "BLOCKED_PENDING_TERMS_REVIEW",
        "universe_count": len(tickers),
        "news_covered": len(news_rows),
        "insider_covered": len(insider_rows),
        "errors": errors,
    }
    (out / "reference_coverage.json").write_text(json.dumps(coverage, ensure_ascii=False, indent=2), encoding="utf-8")
    if len(news_rows) < len(tickers) * 0.95 or len(insider_rows) < len(tickers) * 0.95:
        raise RuntimeError(f"reference coverage too low: news={len(news_rows)}, insider={len(insider_rows)}, universe={len(tickers)}")


if __name__ == "__main__":
    main()
