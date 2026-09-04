from __future__ import annotations

from pathlib import Path
import re

TARGET = Path("scripts/acquire_vsdc_corporate_actions.py")
text = TARGET.read_text(encoding="utf-8")

text = text.replace(
    'BASE = "https://www.vsd.vn/vi/lich-giao-dich"',
    'BASE = "https://vsdc.vn/vi/lich-giao-dich"',
    1,
)

visible_anchor = '''def _visible_text(html: str) -> str:\n    text = re.sub(r"<[^>]+>", " ", html or "")\n    return re.sub(r"\\s+", " ", unescape(text)).strip()\n'''
token_helper = '''def _visible_text(html: str) -> str:\n    text = re.sub(r"<[^>]+>", " ", html or "")\n    return re.sub(r"\\s+", " ", unescape(text)).strip()\n\n\ndef _extract_vptoken(html: str) -> str:\n    for tag in re.findall(r"<meta\\b[^>]*>", html or "", flags=re.I):\n        if not re.search(r"\\bname\\s*=\\s*['\\\"]__VPToken['\\\"]", tag, flags=re.I):\n            continue\n        match = re.search(r"\\bcontent\\s*=\\s*(['\\\"])(.*?)\\1", tag, flags=re.I | re.S)\n        if match:\n            return unescape(match.group(2)).strip()\n    return ""\n'''
if "def _extract_vptoken" not in text:
    if visible_anchor not in text:
        raise SystemExit("visible-text anchor not found; refusing broad patch")
    text = text.replace(visible_anchor, token_helper, 1)

new_fetch_block = '''def fetch_initial_page(session: requests.Session, day: date, retries: int = 3) -> tuple[str, str]:\n    date_value = day.strftime("%d/%m/%Y")\n    url = f"{BASE}?date={quote(date_value)}&tab=LICH_THQ"\n    last = None\n    for attempt in range(retries):\n        try:\n            response = session.get(url, headers=HEADERS, timeout=18)\n            response.raise_for_status()\n            token = _extract_vptoken(response.text)\n            if not token:\n                raise RuntimeError("VSDC GET succeeded but meta __VPToken is missing")\n            return response.text, token\n        except Exception as exc:\n            last = exc\n            time.sleep(min(4.0, 0.5 * (2**attempt)))\n    raise RuntimeError(f"VSDC fetch failed {date_value}: {last}")\n\n\ndef fetch_search_page(\n    session: requests.Session,\n    day: date,\n    page: int,\n    record_on_page: int,\n    vp_token: str,\n    retries: int = 3,\n) -> str:\n    date_value = day.strftime("%d/%m/%Y")\n    search_key = f"|||{date_value}|{date_value}|VI"\n    payload = {\n        "SearchKey": search_key,\n        "CurrentPage": int(page),\n        "RecordOnPage": int(record_on_page),\n        "OrderBy": "",\n        "OrderType": "",\n    }\n    url = f"{_origin()}{SEARCH_ENDPOINT}"\n    headers = {\n        **HEADERS,\n        "Accept": "*/*",\n        "Content-Type": "application/json;charset=utf-8",\n        "Referer": f"{BASE}?date={quote(date_value)}&tab=LICH_THQ",\n        "Origin": _origin(),\n        "X-Requested-With": "XMLHttpRequest",\n        "__VPToken": vp_token,\n    }\n    last = None\n    for attempt in range(retries):\n        try:\n            response = session.post(url, headers=headers, json=payload, timeout=18)\n            response.raise_for_status()\n            return response.text\n        except Exception as exc:\n            last = exc\n            time.sleep(min(4.0, 0.5 * (2**attempt)))\n    raise RuntimeError(f"VSDC page fetch failed {date_value} page={page}: {last}")\n'''
fetch_pattern = re.compile(r"def fetch_html\(.*?\n\ndef parse_tables", re.S)
if "def fetch_initial_page" not in text:
    match = fetch_pattern.search(text)
    if not match:
        raise SystemExit("fetch block not found; refusing broad patch")
    text = text[:match.start()] + new_fetch_block + "\n\ndef parse_tables" + text[match.end():]

new_fetch_one = '''def fetch_one(day: date) -> tuple[date, list[dict[str, object]], dict[str, object], str | None]:\n    session = requests.Session()\n    try:\n        first_html, vp_token = fetch_initial_page(session, day)\n        meta = pagination_meta(first_html)\n        first_rows, first_raw = parse_tables(first_html, day)\n        total = meta.get("total")\n        if total is None:\n            stats = {\n                "advertised_total": None,\n                "raw_rows": first_raw,\n                "pages_expected": None,\n                "pages_fetched": 1,\n                "pagination_complete": False,\n                "reason": "PAGINATION_META_MISSING",\n            }\n            return day, first_rows, stats, None\n\n        total = int(total)\n        record_on_page = int(meta.get("record_on_page") or 10)\n        pages_expected = max(1, math.ceil(total / max(record_on_page, 1))) if total > 0 else 1\n        rows = list(first_rows)\n        raw_rows = int(first_raw)\n        pages_fetched = 1\n        display_mismatches = []\n\n        for page in range(2, pages_expected + 1):\n            page_html = fetch_search_page(session, day, page, record_on_page, vp_token)\n            page_meta = pagination_meta(page_html)\n            page_rows, page_raw = parse_tables(page_html, day)\n            rows.extend(page_rows)\n            raw_rows += int(page_raw)\n            pages_fetched += 1\n            expected_first = (page - 1) * record_on_page + 1\n            if page_meta.get("first") != expected_first or page_meta.get("total") != total:\n                display_mismatches.append({\n                    "page": page,\n                    "expected_first": expected_first,\n                    "actual_first": page_meta.get("first"),\n                    "expected_total": total,\n                    "actual_total": page_meta.get("total"),\n                })\n\n        complete = pages_fetched == pages_expected and raw_rows >= total and not display_mismatches\n        stats = {\n            "advertised_total": total,\n            "raw_rows": raw_rows,\n            "pages_expected": pages_expected,\n            "pages_fetched": pages_fetched,\n            "pagination_complete": bool(complete),\n            "page_display_mismatch_count": len(display_mismatches),\n            "reason": "PASS" if complete else ("PAGE_DISPLAY_MISMATCH" if display_mismatches else "RAW_ROWS_BELOW_ADVERTISED_TOTAL"),\n        }\n        return day, rows, stats, None\n    except Exception as exc:\n        return day, [], {\n            "advertised_total": None,\n            "raw_rows": 0,\n            "pages_expected": None,\n            "pages_fetched": 0,\n            "pagination_complete": False,\n            "page_display_mismatch_count": 0,\n            "reason": "FETCH_OR_PARSE_ERROR",\n        }, str(exc)\n    finally:\n        session.close()\n'''
fetch_one_pattern = re.compile(r"def fetch_one\(.*?\n\ndef main\(\) -> None:", re.S)
match = fetch_one_pattern.search(text)
if not match:
    raise SystemExit("fetch_one block not found; refusing broad patch")
text = text[:match.start()] + new_fetch_one + "\n\ndef main() -> None:" + text[match.end():]

TARGET.write_text(text, encoding="utf-8")
print("patched VSDC collector with same-session VPToken pagination")
