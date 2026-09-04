#!/usr/bin/env python3
from __future__ import annotations

import argparse
import concurrent.futures as cf
from datetime import date, datetime, timedelta, timezone
from io import StringIO
import json
from pathlib import Path
import re
import time
from urllib.parse import quote

import pandas as pd
import requests

BASE = "https://www.vsd.vn/vi/lich-giao-dich"
SOURCE = "VSDC_CORPORATE_ACTION_CALENDAR_INTERNAL"
HEADERS = {
    "User-Agent": "StockRadar-Internal-Research/1.0",
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.7",
}


def valid_ticker(value: object) -> str:
    ticker = str(value or "").strip().upper()
    if len(ticker) != 3 or not ticker.isascii() or not ticker.isalnum() or not any(c.isalpha() for c in ticker):
        return ""
    return ticker


def normalize_col(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def fetch_html(day: date, retries: int = 3) -> str:
    date_value = day.strftime("%d/%m/%Y")
    url = f"{BASE}?date={quote(date_value)}&tab=LICH_THQ"
    last = None
    with requests.Session() as session:
        for attempt in range(retries):
            try:
                r = session.get(url, headers=HEADERS, timeout=18)
                r.raise_for_status()
                return r.text
            except Exception as exc:
                last = exc
                time.sleep(min(4.0, 0.5 * (2**attempt)))
    raise RuntimeError(f"VSDC fetch failed {date_value}: {last}")


def parse_tables(html: str, requested_day: date) -> list[dict[str, object]]:
    try:
        tables = pd.read_html(StringIO(html))
    except ValueError:
        return []
    rows: list[dict[str, object]] = []
    for table in tables:
        table.columns = [normalize_col(c) for c in table.columns]
        ticker_col = next((c for c in table.columns if "mã ck" in c.casefold()), None)
        market_col = next((c for c in table.columns if "thị trường" in c.casefold()), None)
        title_col = next((c for c in table.columns if "tiêu đề" in c.casefold()), None)
        record_col = next((c for c in table.columns if "ngày đkcc" in c.casefold()), None)
        type_col = next((c for c in table.columns if "loại chứng khoán" in c.casefold()), None)
        isin_col = next((c for c in table.columns if "isin" in c.casefold()), None)
        if not ticker_col or not record_col or not title_col:
            continue
        for _, row in table.iterrows():
            ticker = valid_ticker(row.get(ticker_col))
            market = normalize_col(row.get(market_col)) if market_col else ""
            security_type = normalize_col(row.get(type_col)) if type_col else ""
            if not ticker:
                continue
            if market and "HOSE" not in market.upper():
                continue
            if security_type and "CỔ PHIẾU" not in security_type.upper():
                continue
            record_date = pd.to_datetime(row.get(record_col), dayfirst=True, errors="coerce")
            rows.append({
                "ticker": ticker,
                "record_date": record_date.date().isoformat() if pd.notna(record_date) else requested_day.isoformat(),
                "title": normalize_col(row.get(title_col)),
                "isin": normalize_col(row.get(isin_col)) if isin_col else "",
                "market": market or "HOSE",
                "security_type": security_type or "Cổ phiếu",
                "calendar_date_requested": requested_day.isoformat(),
                "source": SOURCE,
                "source_url": f"{BASE}?date={quote(requested_day.strftime('%d/%m/%Y'))}&tab=LICH_THQ",
            })
    return rows


def classify(title: str) -> str:
    value = title.casefold()
    rules = (
        (("cổ tức", "dividend"), "DIVIDEND"),
        (("quyền mua", "phát hành", "chào bán"), "RIGHTS_OR_ISSUANCE"),
        (("đại hội", "đhđcđ"), "SHAREHOLDER_MEETING"),
        (("lấy ý kiến", "ý kiến cổ đông"), "SHAREHOLDER_VOTE"),
        (("thưởng cổ phiếu", "cổ phiếu thưởng"), "BONUS_SHARES"),
    )
    for keywords, label in rules:
        if any(k in value for k in keywords):
            return label
    return "OTHER_RIGHT"


def daterange(start: date, end: date) -> list[date]:
    days: list[date] = []
    day = start
    while day <= end:
        days.append(day)
        day += timedelta(days=1)
    return days


def fetch_one(day: date) -> tuple[date, list[dict[str, object]], str | None]:
    try:
        html = fetch_html(day)
        return day, parse_tables(html, day), None
    except Exception as exc:
        return day, [], str(exc)


def main() -> None:
    parser = argparse.ArgumentParser(description="Acquire current HOSE corporate-action calendar rows from VSDC for internal StockRadar QA/research.")
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--output-dir", default="artifacts/vsdc-corporate-actions")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)
    if end < start:
        raise SystemExit("end must be >= start")
    if (end - start).days > 370:
        raise SystemExit("single acquisition window capped at 371 calendar days")
    workers = max(1, min(int(args.workers), 12))

    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    errors: list[dict[str, str]] = []
    days = daterange(start, end)
    fetched_days = 0

    with cf.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(fetch_one, day) for day in days]
        for future in cf.as_completed(futures):
            day, day_rows, error = future.result()
            if error:
                errors.append({"date": day.isoformat(), "error": error})
            else:
                fetched_days += 1
                rows.extend(day_rows)

    df = pd.DataFrame(rows)
    if df.empty:
        df = pd.DataFrame(columns=["ticker", "record_date", "title", "isin", "market", "security_type", "calendar_date_requested", "source", "source_url", "event_type"])
    else:
        df["event_type"] = df["title"].map(classify)
        df = df.drop_duplicates(subset=["ticker", "record_date", "title"]).sort_values(["record_date", "ticker", "title"])

    csv_path = output / "vsdc_hose_corporate_actions_current.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    coverage = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": SOURCE,
        "window_start": start.isoformat(),
        "window_end": end.isoformat(),
        "days_requested": len(days),
        "days_fetched": fetched_days,
        "days_failed": len(errors),
        "workers": workers,
        "row_count": int(len(df)),
        "unique_tickers": int(df["ticker"].nunique()) if not df.empty else 0,
        "event_type_counts": df["event_type"].value_counts().to_dict() if not df.empty else {},
        "errors": errors,
        "internal_use_only": True,
        "publication_allowed": False,
        "note": "VSDC is used as an authoritative event/reference input. Public redistribution remains separately gated by legal/data-rights approval.",
    }
    (output / "vsdc_hose_corporate_actions_coverage.json").write_text(json.dumps(coverage, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(coverage, ensure_ascii=False))


if __name__ == "__main__":
    main()
