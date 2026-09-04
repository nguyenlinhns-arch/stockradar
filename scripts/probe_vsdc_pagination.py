#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from bs4 import BeautifulSoup
import requests
from urllib.parse import quote

BASE = "https://vsdc.vn/vi/lich-giao-dich"
HEADERS = {"User-Agent": "StockRadar-Internal-Research/1.0", "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.7"}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--date", default="27/07/2026")
    args = p.parse_args()
    url = f"{BASE}?date={quote(args.date)}&tab=LICH_THQ"
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    html = r.text
    soup = BeautifulSoup(html, "html.parser")
    text = " ".join(soup.stripped_strings)
    m = re.search(r"Hiển thị:\s*(\d+)\s*-\s*(\d+)\s*/\s*(\d+)\s*bản ghi", text, re.I)
    summary = {"url": url, "html_bytes": len(html), "display": m.groups() if m else None}
    candidates = []
    for tag in soup.find_all(["a", "button"]):
        label = " ".join(tag.stripped_strings).strip()
        href = tag.get("href") or ""
        onclick = tag.get("onclick") or ""
        blob = f"{label} {href} {onclick}"
        if re.search(r"page|trang|LICH_THQ|^\s*\d+\s*$|next|prev|>>|<<", blob, re.I):
            candidates.append({"tag": tag.name, "label": label, "href": href, "onclick": onclick})
    inputs = []
    for tag in soup.find_all(["input", "select"]):
        name = tag.get("name") or ""
        ident = tag.get("id") or ""
        value = tag.get("value") or ""
        if re.search(r"page|tab|date|limit|size|record", f"{name} {ident} {value}", re.I):
            inputs.append({"tag": tag.name, "name": name, "id": ident, "value": value})
    print(json.dumps({"summary": summary, "pagination_candidates": candidates[:100], "inputs": inputs[:100]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
