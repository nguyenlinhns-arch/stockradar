#!/usr/bin/env python3
from __future__ import annotations

import argparse
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
    "User-Agent": "StockRadar-Internal-Research/3.0",
    "x-lang": "vi",
}
SOURCE = "KBS_PUBLIC_EVENT_BOOTSTRAP_INTERNAL_ONLY"
EVENT_TYPES = {
    1: "SHAREHOLDER_MEETING",
    2: "DIVIDEND",
    3: "ISSUANCE",
    4: "INSIDER_TRADING",
    5: "OTHER",
}
PAGE_SIZE = 50
MAX_PAGES = 8


def clean_symbol(value: Any) -> str:
    s = str(value or "").strip().upper()
    return s if len(s) == 3 and s.isascii() and s.isalnum() and any(c.isalpha() for c in s) else ""


def request_json(session: requests.Session, path: str, params=None, retries=4):
    url = f"{BASE}{path}"
    last = None
    for attempt in range(retries):
        try:
            r = session.get(url, params=params, headers=HEADERS, timeout=25)
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            last = exc
            time.sleep(min(6.0, 0.6 * (2**attempt)))
    raise RuntimeError(f"GET failed {url}: {last}")


def items(payload):
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for key in ("items", "data", "Data", "Content", "events", "result", "Result"):
            value = payload.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
        if any(k in payload for k in ("EventID", "Title", "ReportDate", "GDKHQDate")):
            return [payload]
    return []


def identity(item: dict) -> str:
    for key in ("EventID", "ID", "Title", "ReportDate", "GDKHQDate"):
        value = item.get(key)
        if value not in (None, ""):
            return f"{key}:{value}"
    return json.dumps(item, ensure_ascii=False, sort_keys=True, default=str)


def fetch_universe() -> list[str]:
    with requests.Session() as s:
        listing = request_json(s, "/stock/search/data")
    tickers = []
    for item in listing if isinstance(listing, list) else []:
        ticker = clean_symbol(item.get("symbol"))
        if ticker and str(item.get("exchange") or "").upper() == "HOSE" and str(item.get("type") or "stock").lower() in {"stock", "equity", ""}:
            tickers.append(ticker)
    return sorted(set(tickers))


def fetch_type(session: requests.Session, ticker: str, event_id: int) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    empty_streak = 0
    for page in range(1, MAX_PAGES + 1):
        payload = request_json(
            session,
            f"/stockinfo/event/{ticker}",
            {"l": 1, "p": page, "s": PAGE_SIZE, "eID": event_id},
        )
        batch = items(payload)
        new = 0
        for item in batch:
            key = identity(item)
            if key not in seen:
                seen.add(key)
                record = dict(item)
                record["_event_type_id"] = event_id
                record["_event_type"] = EVENT_TYPES[event_id]
                out.append(record)
                new += 1
        if not batch or new == 0:
            empty_streak += 1
        else:
            empty_streak = 0
        if empty_streak >= 2:
            break
        if len(batch) < PAGE_SIZE and page > 1:
            break
    return out


def fetch_one(ticker: str):
    try:
        events: list[dict] = []
        with requests.Session() as s:
            for event_id in EVENT_TYPES:
                events.extend(fetch_type(s, ticker, event_id))
        # Cross-type duplicates can occur. Keep event type in identity because it is semantically useful.
        dedup: dict[str, dict] = {}
        for event in events:
            key = f"{event.get('_event_type_id')}|{identity(event)}"
            dedup[key] = event
        return ticker, list(dedup.values()), None
    except Exception as exc:
        return ticker, [], str(exc)


def extract_date(item: dict):
    for key in ("GDKHQDate", "ReportDate", "NDKCCDate", "PublishTime", "Date", "Time"):
        value = item.get(key)
        if value not in (None, ""):
            dt = pd.to_datetime(value, errors="coerce")
            if pd.notna(dt):
                return dt
    return pd.NaT


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir", default="artifacts/kbs-events-depth-v3")
    p.add_argument("--workers", type=int, default=10)
    args = p.parse_args()
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)

    tickers = fetch_universe()
    if len(tickers) < 405:
        raise RuntimeError(f"HOSE universe unexpectedly small: {len(tickers)}")

    rows = []
    flat_rows = []
    errors = []
    workers = max(1, min(int(args.workers), 12))
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(fetch_one, t) for t in tickers]
        for future in cf.as_completed(futures):
            ticker, events, error = future.result()
            if error:
                errors.append({"ticker": ticker, "error": error})
            rows.append({
                "ticker": ticker,
                "source": SOURCE,
                "event_count": len(events),
                "payload": json.dumps(events, ensure_ascii=False, separators=(",", ":"), default=str),
            })
            for event in events:
                flat_rows.append({
                    "ticker": ticker,
                    "event_type_id": event.get("_event_type_id"),
                    "event_type": event.get("_event_type"),
                    "event_date": extract_date(event),
                    "title": event.get("Title") or event.get("EventName") or event.get("Reason") or "",
                    "record_date": event.get("NDKCCDate") or event.get("ReportDate"),
                    "ex_right_date": event.get("GDKHQDate"),
                    "raw_event_id": event.get("EventID") or event.get("ID"),
                    "source": SOURCE,
                    "raw_json": json.dumps(event, ensure_ascii=False, separators=(",", ":"), default=str),
                })

    raw = pd.DataFrame(rows).sort_values("ticker")
    flat = pd.DataFrame(flat_rows)
    if not flat.empty:
        flat["event_date"] = pd.to_datetime(flat["event_date"], errors="coerce")
        flat = flat.sort_values(["ticker", "event_date"], ascending=[True, False], na_position="last")
    raw.to_csv(output / "kbs_company_events_depth_v3.csv", index=False, encoding="utf-8-sig")
    flat.to_csv(output / "kbs_company_events_flat_v3.csv", index=False, encoding="utf-8-sig")

    now = pd.Timestamp("2026-09-04")
    current90 = 0
    current365 = 0
    if not flat.empty:
        ages = (now - flat["event_date"].dt.normalize()).dt.days
        current90 = int(ages.between(0, 90, inclusive="both").sum())
        current365 = int(ages.between(0, 365, inclusive="both").sum())
    coverage = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": SOURCE,
        "canonical_hose": len(tickers),
        "ticker_rows": len(raw),
        "event_rows": len(flat),
        "tickers_with_events": int((raw["event_count"] > 0).sum()),
        "events_with_dates": int(flat["event_date"].notna().sum()) if not flat.empty else 0,
        "events_last_90d_asof_2026_09_04": current90,
        "events_last_365d_asof_2026_09_04": current365,
        "event_type_counts": flat["event_type"].value_counts().to_dict() if not flat.empty else {},
        "errors": errors,
        "internal_use_only": True,
        "publication_allowed": False,
        "note": "KBS event feed is an internal operational/reference source. Sensitive corporate actions must still be reconciled against VSDC/HOSE before public action.",
    }
    (output / "kbs_company_events_coverage_v3.json").write_text(json.dumps(coverage, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(coverage, ensure_ascii=False))


if __name__ == "__main__":
    main()
