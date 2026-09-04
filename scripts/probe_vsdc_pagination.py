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
HEADERS = {
    "User-Agent": "StockRadar-Internal-Research/1.0",
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.7",
}


def function_window(text: str, name: str, before: int = 250, after: int = 5000) -> str:
    needles = [f"function {name}", f"{name} = function", name]
    idx = next((text.find(n) for n in needles if text.find(n) >= 0), -1)
    if idx < 0:
        return ""
    return text[max(0, idx - before): min(len(text), idx + after)]


def occurrence_windows(text: str, needle: str, radius: int = 700, limit: int = 30) -> list[str]:
    out: list[str] = []
    start = 0
    while len(out) < limit:
        idx = text.find(needle, start)
        if idx < 0:
            break
        out.append(text[max(0, idx - radius): min(len(text), idx + radius)])
        start = idx + max(1, len(needle))
    return out


def display_meta(text: str) -> dict[str, int] | None:
    visible = " ".join(BeautifulSoup(text, "html.parser").stripped_strings)
    m = re.search(r"Hiển thị:\s*(\d+)\s*-\s*(\d+)\s*/\s*(\d+)\s*bản ghi", visible, re.I)
    if not m:
        return None
    first, last, total = (int(x) for x in m.groups())
    return {"first": first, "last": last, "total": total}


def parse_js_number(script: str, name: str) -> int | None:
    for pattern in [
        rf"(?:var|let|const)\s+{re.escape(name)}\s*=\s*['\"]?(\d+)",
        rf"\b{re.escape(name)}\s*=\s*['\"]?(\d+)",
    ]:
        m = re.search(pattern, script, re.I)
        if m:
            return int(m.group(1))
    return None


def js_string_assignments(script: str, name: str) -> list[str]:
    values: list[str] = []
    patterns = [
        rf"(?:var|let|const)\s+{re.escape(name)}\s*=\s*(['\"])(.*?)\1",
        rf"(?<![\w$]){re.escape(name)}\s*=\s*(['\"])(.*?)\1",
    ]
    for pattern in patterns:
        for m in re.finditer(pattern, script, re.I | re.S):
            value = m.group(2)
            if value not in values:
                values.append(value)
    return values[:30]


def safe_response(response: requests.Response) -> dict[str, object]:
    preview = re.sub(r"\s+", " ", response.text[:1000]).strip()
    return {
        "status": response.status_code,
        "content_type": response.headers.get("content-type", ""),
        "bytes": len(response.content),
        "display": display_meta(response.text),
        "preview": preview,
    }


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
    first_display = display_meta(html)

    inline_scripts = "\n\n".join((tag.string or tag.get_text(" ") or "") for tag in soup.find_all("script") if not tag.get("src"))
    record_on_page = parse_js_number(inline_scripts, "recordOnPage") or 10
    current_page = parse_js_number(inline_scripts, "currentPage") or 1
    key_assignments_inline = js_string_assignments(inline_scripts, "keySearch")

    date_from = ((soup.find(id="txtSearchLichTHQ_TuNgay") or {}).get("value") if soup.find(id="txtSearchLichTHQ_TuNgay") else None) or args.date
    date_to = ((soup.find(id="txtSearchLichTHQ_DenNgay") or {}).get("value") if soup.find(id="txtSearchLichTHQ_DenNgay") else None) or args.date
    stock = ((soup.find(id="txtSearchLichTHQ_MaCK") or {}).get("value") if soup.find(id="txtSearchLichTHQ_MaCK") else None) or ""
    sec_type = ((soup.find(id="txtSearchLichTHQ_LoaiCK") or {}).get("value") if soup.find(id="txtSearchLichTHQ_LoaiCK") else None) or ""
    market = ((soup.find(id="txtSearchLichTHQ_ThiTruong") or {}).get("value") if soup.find(id="txtSearchLichTHQ_ThiTruong") else None) or ""
    derived_search_key = f"{stock}|{sec_type}|{market}|{date_from}|{date_to}|VI"

    hidden_inputs = []
    for tag in soup.find_all("input"):
        name = tag.get("name") or ""
        ident = tag.get("id") or ""
        typ = (tag.get("type") or "").lower()
        value = tag.get("value") or ""
        if typ == "hidden" or re.search(r"token|verification|csrf|antiforgery", f"{name} {ident}", re.I):
            hidden_inputs.append({"name": name, "id": ident, "type": typ, "value_present": bool(value), "value_length": len(value)})

    cookie_summary = [
        {
            "name": c.name,
            "domain": c.domain,
            "path": c.path,
            "secure": bool(c.secure),
            "rest_keys": sorted((c._rest or {}).keys()),
            "value_length": len(c.value or ""),
        }
        for c in session.cookies
    ]

    script_diagnostics = []
    all_script_texts = [("inline", inline_scripts)]
    for tag in soup.find_all("script"):
        src = tag.get("src")
        if not src:
            continue
        full = urljoin(ORIGIN, src)
        try:
            js = session.get(full, headers=HEADERS, timeout=20)
            js.raise_for_status()
            all_script_texts.append((full, js.text))
        except Exception as exc:
            script_diagnostics.append({"source": full, "fetch_error": str(exc)})

    diagnostic_needles = ["__VPToken", "ajaxSetup", "document.cookie", "RequestVerificationToken", "X-Requested-With", "keySearch", "recordOnPage"]
    for source, text in all_script_texts:
        hits = {}
        for needle in diagnostic_needles:
            windows = occurrence_windows(text, needle, 650, 12)
            if windows:
                hits[needle] = windows
        if hits:
            script_diagnostics.append({
                "source": source,
                "keySearch_string_assignments": js_string_assignments(text, "keySearch"),
                "hits": hits,
            })

    endpoint = f"{ORIGIN}/lich-thq/search"
    base_headers = {
        **HEADERS,
        "Accept": "*/*",
        "Content-Type": "application/json;charset=utf-8",
        "Referer": url,
        "Origin": ORIGIN,
    }
    search_keys = [
        ("derived_date", derived_search_key),
        ("empty", ""),
        ("unfiltered_vi", "|||||VI"),
    ]
    for value in key_assignments_inline:
        if value not in {v for _, v in search_keys}:
            search_keys.append((f"inline_assignment_{len(search_keys)}", value))

    post_results = []
    for key_label, search_key in search_keys:
        payload = {
            "SearchKey": search_key,
            "CurrentPage": 2,
            "RecordOnPage": int(record_on_page),
            "OrderBy": "",
            "OrderType": "",
        }
        variants = [
            ("basic", dict(base_headers)),
            ("xhr", {**base_headers, "X-Requested-With": "XMLHttpRequest"}),
        ]
        for header_label, headers in variants:
            try:
                resp = session.post(endpoint, headers=headers, json=payload, timeout=20)
                post_results.append({
                    "search_key_variant": key_label,
                    "search_key_length": len(search_key),
                    "header_variant": header_label,
                    **safe_response(resp),
                })
            except Exception as exc:
                post_results.append({"search_key_variant": key_label, "header_variant": header_label, "exception": str(exc)})

    print(json.dumps({
        "summary": {
            "url": url,
            "display": first_display,
            "cookies": cookie_summary,
            "hidden_inputs": hidden_inputs,
        },
        "state": {
            "recordOnPage": record_on_page,
            "currentPage": current_page,
            "keySearch_string_assignments_inline": key_assignments_inline,
            "derived_search_key": derived_search_key,
        },
        "inline_changePage": function_window(inline_scripts, "changePage_LichTHQ", after=1800),
        "inline_tablLichTHQ": function_window(inline_scripts, "tablLichTHQ", after=4200),
        "script_diagnostics": script_diagnostics,
        "post_page2_results": post_results,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
