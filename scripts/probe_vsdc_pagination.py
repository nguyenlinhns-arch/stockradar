#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from bs4 import BeautifulSoup
import requests
from urllib.parse import quote

BASE = "https://vsdc.vn/vi/lich-giao-dich"
ORIGIN = "https://vsdc.vn"
HEADERS = {
    "User-Agent": "StockRadar-Internal-Research/1.0",
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.7",
}


def display_meta(html: str) -> dict[str, int] | None:
    visible = " ".join(BeautifulSoup(html, "html.parser").stripped_strings)
    m = re.search(r"Hiển thị:\s*(\d+)\s*-\s*(\d+)\s*/\s*(\d+)\s*bản ghi", visible, re.I)
    if not m:
        return None
    first, last, total = (int(x) for x in m.groups())
    return {"first": first, "last": last, "total": total}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--date", default="27/07/2026")
    args = p.parse_args()
    url = f"{BASE}?date={quote(args.date)}&tab=LICH_THQ"

    session = requests.Session()
    first = session.get(url, headers=HEADERS, timeout=20)
    first.raise_for_status()
    soup = BeautifulSoup(first.text, "html.parser")
    scripts = "\n".join((s.string or s.get_text(" ") or "") for s in soup.find_all("script") if not s.get("src"))

    record_match = re.search(r"recordOnPage\s*=\s*['\"]?(\d+)", scripts, re.I)
    record_on_page = int(record_match.group(1)) if record_match else 10
    key_matches = re.findall(r"keySearch\s*=\s*(['\"])(.*?)\1", scripts, re.I | re.S)
    key_values = [value for _, value in key_matches]
    target_key = next((v for v in key_values if args.date in v and v.count("|") == 5), f"|||{args.date}|{args.date}|VI")

    token_meta = soup.find("meta", attrs={"name": "__VPToken"})
    token = (token_meta.get("content") if token_meta else None) or ""

    payload = {
        "SearchKey": target_key,
        "CurrentPage": 2,
        "RecordOnPage": record_on_page,
        "OrderBy": "",
        "OrderType": "",
    }
    base_headers = {
        **HEADERS,
        "Accept": "*/*",
        "Content-Type": "application/json;charset=utf-8",
        "Referer": url,
        "Origin": ORIGIN,
        "X-Requested-With": "XMLHttpRequest",
    }

    results = []
    for label, extra in [
        ("same_session_no_vptoken_header", {}),
        ("same_session_meta_vptoken_header", {"__VPToken": token} if token else {}),
    ]:
        response = session.post(f"{ORIGIN}/lich-thq/search", headers={**base_headers, **extra}, json=payload, timeout=20)
        results.append({
            "variant": label,
            "status": response.status_code,
            "bytes": len(response.content),
            "display": display_meta(response.text),
            "preview": re.sub(r"\s+", " ", response.text[:500]).strip(),
        })

    # Do not print token/cookie values to public CI logs.
    print(json.dumps({
        "first_page": display_meta(first.text),
        "record_on_page": record_on_page,
        "target_key_length": len(target_key),
        "target_key_contains_requested_date": args.date in target_key,
        "meta_vptoken_present": bool(token),
        "meta_vptoken_length": len(token),
        "cookie_names": [c.name for c in session.cookies],
        "page2_results": results,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
