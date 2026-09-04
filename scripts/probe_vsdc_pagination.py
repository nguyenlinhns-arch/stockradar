#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from bs4 import BeautifulSoup
import requests
from urllib.parse import quote, urljoin

BASE = "https://vsdc.vn/vi/lich-giao-dich"
ORIGIN = "https://vsdc.vn"
HEADERS = {"User-Agent": "StockRadar-Internal-Research/1.0", "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.7"}
TARGET = "changePage_LichTHQ"


def snippets(text: str, needle: str, radius: int = 900) -> list[str]:
    out: list[str] = []
    start = 0
    while True:
        idx = text.find(needle, start)
        if idx < 0:
            break
        out.append(text[max(0, idx - radius): min(len(text), idx + radius)])
        start = idx + len(needle)
    return out[:20]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--date", default="27/07/2026")
    args = p.parse_args()
    url = f"{BASE}?date={quote(args.date)}&tab=LICH_THQ"
    session = requests.Session()
    r = session.get(url, headers=HEADERS, timeout=20)
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

    html_hits = snippets(html, TARGET)
    script_srcs = []
    script_hits = []
    for tag in soup.find_all("script"):
        src = tag.get("src")
        inline = tag.string or tag.get_text(" ") or ""
        if TARGET in inline:
            script_hits.append({"source": "inline", "snippets": snippets(inline, TARGET)})
        if not src:
            continue
        full = urljoin(ORIGIN, src)
        script_srcs.append(full)
        try:
            js = session.get(full, headers=HEADERS, timeout=20)
            js.raise_for_status()
            if TARGET in js.text or "LichTHQ" in js.text or "LICH_THQ" in js.text:
                script_hits.append({
                    "source": full,
                    "bytes": len(js.text),
                    "target_snippets": snippets(js.text, TARGET),
                    "lichthq_snippets": snippets(js.text, "LichTHQ")[:10],
                })
        except Exception as exc:
            script_hits.append({"source": full, "fetch_error": str(exc)})

    forms = []
    for form in soup.find_all("form"):
        forms.append({
            "action": form.get("action") or "",
            "method": form.get("method") or "",
            "id": form.get("id") or "",
            "class": form.get("class") or [],
        })

    print(json.dumps({
        "summary": summary,
        "pagination_candidates": candidates[:100],
        "inputs": inputs[:100],
        "forms": forms[:30],
        "html_target_snippets": html_hits,
        "script_srcs": script_srcs,
        "script_hits": script_hits,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
