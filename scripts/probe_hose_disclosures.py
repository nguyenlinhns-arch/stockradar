#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from urllib.parse import urljoin, urlparse

import requests

BASE = "https://www.hsx.vn"
DISCLOSURE_PAGE = f"{BASE}/vi/quy-dinh-hose/cong-bo-thong-tin"
LISTED_NEWS_PAGE = f"{BASE}/vi/tin-tuc/tin-to-chuc-niem-yet"
SAMPLE_NEWS = f"{BASE}/Modules/Cms/Web/News/?id=2494315"
HEADERS = {
    "User-Agent": "Mozilla/5.0 StockRadar-Internal-Research/1.0",
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.7",
}
KEYWORDS = (
    "articleincategory", "modules/cms", "cms/web/news", "newsbycat",
    "tin-to-chuc-niem-yet", "cong-bo-thong-tin", "tokenCode", "categoryId",
    "getrelatedfiles", "downloadfile", "pageFieldName", "pageCriteriaLength",
)


def snippets(text: str, needle: str, radius: int = 500, limit: int = 10):
    out = []
    low = text.lower()
    n = needle.lower()
    pos = 0
    while len(out) < limit:
        idx = low.find(n, pos)
        if idx < 0:
            break
        out.append(text[max(0, idx-radius):min(len(text), idx+radius)])
        pos = idx + len(n)
    return out


def inspect_page(session: requests.Session, url: str):
    r = session.get(url, headers=HEADERS, timeout=10)
    r.raise_for_status()
    html = r.text
    script_srcs = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html, flags=re.I)
    same_origin = []
    for src in script_srcs:
        full = urljoin(url, src)
        if urlparse(full).hostname in {"www.hsx.vn", "hsx.vn", "www1.hsx.vn"}:
            same_origin.append(full)
    return html, same_origin[:20]


def main() -> None:
    session = requests.Session()
    page_results = []
    script_urls = []
    for page_url in (DISCLOSURE_PAGE, LISTED_NEWS_PAGE):
        try:
            html, scripts = inspect_page(session, page_url)
            script_urls.extend(scripts)
            page_results.append({
                "url": page_url,
                "bytes": len(html),
                "script_count": len(scripts),
                "html_hits": {kw: snippets(html, kw) for kw in KEYWORDS if snippets(html, kw)},
            })
        except Exception as exc:
            page_results.append({"url": page_url, "error": str(exc)})

    diagnostics = []
    seen = set()
    for url in script_urls:
        if url in seen:
            continue
        seen.add(url)
        try:
            r = session.get(url, headers=HEADERS, timeout=8)
            r.raise_for_status()
            text = r.text
            hits = {kw: snippets(text, kw) for kw in KEYWORDS if snippets(text, kw)}
            if hits:
                diagnostics.append({"url": url, "bytes": len(text), "hits": hits})
        except Exception as exc:
            diagnostics.append({"url": url, "error": str(exc)})

    sample = session.get(SAMPLE_NEWS, headers=HEADERS, timeout=10)
    sample.raise_for_status()
    sample_text = sample.text
    title_match = re.search(r'<title[^>]*>(.*?)</title>', sample_text, flags=re.I | re.S)
    static_refs = sorted(set(re.findall(r'https?://staticfile\.hsx\.vn/[^"\'<>\s]+', sample_text, flags=re.I)))
    related = {kw: snippets(sample_text, kw) for kw in KEYWORDS if snippets(sample_text, kw)}

    result = {
        "pages": page_results,
        "same_origin_scripts_scanned": len(seen),
        "script_diagnostics": diagnostics,
        "sample_news": {
            "url": SAMPLE_NEWS,
            "status": sample.status_code,
            "bytes": len(sample_text),
            "title": re.sub(r'\s+', ' ', title_match.group(1)).strip() if title_match else None,
            "static_refs": static_refs[:20],
            "hits": related,
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
