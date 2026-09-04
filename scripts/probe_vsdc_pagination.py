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


def function_window(text: str, name: str, before: int = 200, after: int = 8000) -> str:
    needles = [f"function {name}", f"{name} = function", name]
    idx = next((text.find(n) for n in needles if text.find(n) >= 0), -1)
    if idx < 0:
        return ""
    return text[max(0, idx - before): min(len(text), idx + after)]


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
        if re.search(r"page|tab|date|limit|size|record|searchlichthq", f"{name} {ident} {value}", re.I):
            inputs.append({"tag": tag.name, "name": name, "id": ident, "value": value})

    inline_scripts = "\n\n".join((tag.string or tag.get_text(" ") or "") for tag in soup.find_all("script") if not tag.get("src"))
    inline_tabl = function_window(inline_scripts, "tablLichTHQ")
    inline_change = function_window(inline_scripts, "changePage_LichTHQ", after=2500)

    script_srcs = []
    external_hits = []
    for tag in soup.find_all("script"):
        src = tag.get("src")
        if not src:
            continue
        full = urljoin(ORIGIN, src)
        script_srcs.append(full)
        try:
            js = session.get(full, headers=HEADERS, timeout=20)
            js.raise_for_status()
            if TARGET in js.text or "LichTHQ" in js.text or "LICH_THQ" in js.text:
                external_hits.append({
                    "source": full,
                    "bytes": len(js.text),
                    "tablLichTHQ_window": function_window(js.text, "tablLichTHQ"),
                    "changePage_window": function_window(js.text, "changePage_LichTHQ", after=2500),
                    "ajax_windows": snippets(js.text, "ajax", 1800)[:10],
                })
        except Exception as exc:
            if "vsdc.vn" in full:
                external_hits.append({"source": full, "fetch_error": str(exc)})

    print(json.dumps({
        "summary": summary,
        "pagination_candidates": candidates[:100],
        "inputs": inputs[:100],
        "inline_changePage_window": inline_change,
        "inline_tablLichTHQ_window": inline_tabl,
        "script_srcs": script_srcs,
        "external_hits": external_hits,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
