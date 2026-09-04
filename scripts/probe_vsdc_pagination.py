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


def display_meta(text: str) -> dict[str, int] | None:
    visible = " ".join(BeautifulSoup(text, "html.parser").stripped_strings)
    m = re.search(r"Hiển thị:\s*(\d+)\s*-\s*(\d+)\s*/\s*(\d+)\s*bản ghi", visible, re.I)
    if not m:
        return None
    first, last, total = (int(x) for x in m.groups())
    return {"first": first, "last": last, "total": total}


def parse_js_number(script: str, name: str) -> int | None:
    patterns = [
        rf"(?:var|let|const)\s+{re.escape(name)}\s*=\s*['\"]?(\d+)",
        rf"\b{re.escape(name)}\s*=\s*['\"]?(\d+)",
    ]
    for pattern in patterns:
        m = re.search(pattern, script, re.I)
        if m:
            return int(m.group(1))
    return None


def parse_js_string(script: str, name: str) -> str | None:
    patterns = [
        rf"(?:var|let|const)\s+{re.escape(name)}\s*=\s*(['\"])(.*?)\1",
        rf"\b{re.escape(name)}\s*=\s*(['\"])(.*?)\1",
    ]
    for pattern in patterns:
        m = re.search(pattern, script, re.I | re.S)
        if m:
            return m.group(2)
    return None


def safe_post_result(response: requests.Response) -> dict[str, object]:
    content_type = response.headers.get("content-type", "")
    preview = re.sub(r"\s+", " ", response.text[:800]).strip()
    return {
        "status": response.status_code,
        "content_type": content_type,
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
    record_on_page_js = parse_js_number(inline_scripts, "recordOnPage")
    current_page_js = parse_js_number(inline_scripts, "currentPage")
    key_search_js = parse_js_string(inline_scripts, "keySearch")

    date_input_from = soup.find(id="txtSearchLichTHQ_TuNgay")
    date_input_to = soup.find(id="txtSearchLichTHQ_DenNgay")
    stock_input = soup.find(id="txtSearchLichTHQ_MaCK")
    type_input = soup.find(id="txtSearchLichTHQ_LoaiCK")
    market_input = soup.find(id="txtSearchLichTHQ_ThiTruong")
    lang = "VI"
    date_from = (date_input_from.get("value") if date_input_from else None) or args.date
    date_to = (date_input_to.get("value") if date_input_to else None) or args.date
    stock = (stock_input.get("value") if stock_input else None) or ""
    sec_type = (type_input.get("value") if type_input else None) or ""
    market = (market_input.get("value") if market_input else None) or ""
    derived_search_key = f"{stock}|{sec_type}|{market}|{date_from}|{date_to}|{lang}"

    # The UI visibly shows 10 rows on the first page. Prefer the server-side JS variable
    # when present, and only fall back to the display width.
    if record_on_page_js:
        record_on_page = record_on_page_js
        record_on_page_source = "inline_js"
    elif first_display:
        record_on_page = max(1, first_display["last"] - first_display["first"] + 1)
        record_on_page_source = "first_page_display"
    else:
        record_on_page = 10
        record_on_page_source = "fallback_10"

    hidden_inputs = []
    token_value = None
    token_name = None
    for tag in soup.find_all("input"):
        name = tag.get("name") or ""
        ident = tag.get("id") or ""
        typ = (tag.get("type") or "").lower()
        value = tag.get("value") or ""
        if typ == "hidden" or re.search(r"token|verification|csrf|antiforgery", f"{name} {ident}", re.I):
            hidden_inputs.append({
                "name": name,
                "id": ident,
                "type": typ,
                "value_present": bool(value),
                "value_length": len(value),
            })
        if value and re.search(r"requestverificationtoken|csrf|antiforgery", f"{name} {ident}", re.I):
            token_name = name or ident
            token_value = value

    cookie_summary = [
        {"name": cookie.name, "domain": cookie.domain, "path": cookie.path, "value_length": len(cookie.value or "")}
        for cookie in session.cookies
    ]

    endpoint = f"{ORIGIN}/lich-thq/search"
    payload = {
        "SearchKey": key_search_js or derived_search_key,
        "CurrentPage": 2,
        "RecordOnPage": int(record_on_page),
        "OrderBy": "",
        "OrderType": "",
    }
    base_headers = {
        **HEADERS,
        "Content-Type": "application/json;charset=utf-8",
        "Accept": "*/*",
        "Referer": url,
        "Origin": ORIGIN,
    }

    variants: list[tuple[str, dict[str, str]]] = [
        ("same_session_basic", dict(base_headers)),
        ("same_session_xhr", {**base_headers, "X-Requested-With": "XMLHttpRequest"}),
    ]
    if token_name and token_value:
        variants.extend([
            ("same_session_token_header", {**base_headers, token_name: token_value}),
            ("same_session_xhr_token_header", {**base_headers, "X-Requested-With": "XMLHttpRequest", token_name: token_value}),
            ("same_session_requestverificationtoken_header", {**base_headers, "X-Requested-With": "XMLHttpRequest", "RequestVerificationToken": token_value}),
        ])

    post_results = []
    for label, headers in variants:
        try:
            resp = session.post(endpoint, headers=headers, json=payload, timeout=20)
            post_results.append({"variant": label, **safe_post_result(resp)})
        except Exception as exc:
            post_results.append({"variant": label, "exception": str(exc)})

    candidates = []
    for tag in soup.find_all(["a", "button"]):
        label = " ".join(tag.stripped_strings).strip()
        href = tag.get("href") or ""
        onclick = tag.get("onclick") or ""
        blob = f"{label} {href} {onclick}"
        if re.search(r"page|trang|LICH_THQ|^\s*\d+\s*$|next|prev|>>|<<", blob, re.I):
            candidates.append({"tag": tag.name, "label": label, "href": href, "onclick": onclick})

    inline_tabl = function_window(inline_scripts, "tablLichTHQ")
    inline_change = function_window(inline_scripts, "changePage_LichTHQ", after=2500)

    # Never print cookie/token values; only presence and lengths are exposed in CI logs.
    print(json.dumps({
        "summary": {
            "url": url,
            "html_bytes": len(html),
            "display": first_display,
            "cookies": cookie_summary,
            "hidden_inputs": hidden_inputs,
            "token_detected": bool(token_value),
            "token_name": token_name,
        },
        "state": {
            "recordOnPage_js": record_on_page_js,
            "recordOnPage_used": record_on_page,
            "recordOnPage_source": record_on_page_source,
            "currentPage_js": current_page_js,
            "keySearch_js_present": key_search_js is not None,
            "keySearch_js_length": len(key_search_js or ""),
            "derived_search_key": derived_search_key,
            "payload_without_sensitive_values": payload,
        },
        "pagination_candidates": candidates[:50],
        "inline_changePage_window": inline_change,
        "inline_tablLichTHQ_window": inline_tabl,
        "post_page2_results": post_results,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
