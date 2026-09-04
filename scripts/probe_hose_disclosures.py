#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from urllib.parse import urljoin

import requests

BASE = "https://www.hsx.vn"
DISCLOSURE_PAGE = f"{BASE}/vi/quy-dinh-hose/cong-bo-thong-tin"
SAMPLE_NEWS = f"{BASE}/Modules/Cms/Web/News/?id=2494315"
HEADERS = {
    "User-Agent": "Mozilla/5.0 StockRadar-Internal-Research/1.0",
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.7",
}
KEYWORDS = (
    "modules/cms", "cms/web/news", "cong-bo-thong-tin", "disclosure",
    "news", "api/", "graphql", "search", "getlist", "pageindex",
)


def snippets(text: str, needle: str, radius: int = 400, limit: int = 12):
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


def main() -> None:
    session = requests.Session()
    page = session.get(DISCLOSURE_PAGE, headers=HEADERS, timeout=30)
    page.raise_for_status()
    html = page.text

    script_srcs = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html, flags=re.I)
    script_urls = [urljoin(DISCLOSURE_PAGE, s) for s in script_srcs]
    diagnostics = []
    for url in script_urls:
        try:
            r = session.get(url, headers=HEADERS, timeout=30)
            r.raise_for_status()
            text = r.text
            hits = {}
            for kw in KEYWORDS:
                snips = snippets(text, kw)
                if snips:
                    hits[kw] = snips
            if hits:
                diagnostics.append({"url": url, "bytes": len(text), "hits": hits})
        except Exception as exc:
            diagnostics.append({"url": url, "error": str(exc)})

    sample = session.get(SAMPLE_NEWS, headers=HEADERS, timeout=30)
    sample.raise_for_status()
    sample_text = sample.text
    title_match = re.search(r'<title[^>]*>(.*?)</title>', sample_text, flags=re.I | re.S)
    pdfs = sorted(set(re.findall(r'https?://[^"\'<>\s]+\.pdf(?:\?[^"\'<>\s]*)?', sample_text, flags=re.I)))
    static_refs = sorted(set(re.findall(r'https?://staticfile\.hsx\.vn/[^"\'<>\s]+', sample_text, flags=re.I)))

    result = {
        "disclosure_page": {
            "url": DISCLOSURE_PAGE,
            "status": page.status_code,
            "bytes": len(html),
            "script_count": len(script_urls),
            "script_urls": script_urls,
            "html_modules_cms_snippets": snippets(html, "Modules/Cms"),
            "html_api_snippets": snippets(html, "api/"),
        },
        "script_diagnostics": diagnostics,
        "sample_news": {
            "url": SAMPLE_NEWS,
            "status": sample.status_code,
            "bytes": len(sample_text),
            "title": re.sub(r'\s+', ' ', title_match.group(1)).strip() if title_match else None,
            "static_refs": static_refs[:20],
            "pdfs": pdfs[:20],
            "modules_snippets": snippets(sample_text, "Modules/Cms"),
            "attachment_snippets": snippets(sample_text, "staticfile.hsx.vn"),
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
