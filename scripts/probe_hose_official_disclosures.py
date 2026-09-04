#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE = "https://www.hsx.vn"
TARGETS = [
    "/vi/quy-dinh-hose/cong-bo-thong-tin",
    "/vi/tin-tuc/thong-tin-cong-bo-hose",
    "/vi/quan-ly-niem-yet/co-phieu",
]
HEADERS = {
    "User-Agent": "Mozilla/5.0 StockRadar-Internal-Research/1.0",
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.7",
}

KEYWORDS = (
    "rss", "cong-bo", "congbothongtin", "disclosure", "article", "news",
    "api/", "graphql", "odata", "search", "listed", "niemyet", "issuer",
)


def snippets(text: str, needle: str, radius: int = 600) -> list[str]:
    out = []
    low = text.casefold()
    nlow = needle.casefold()
    start = 0
    while True:
        idx = low.find(nlow, start)
        if idx < 0:
            break
        out.append(text[max(0, idx-radius): min(len(text), idx+radius)])
        start = idx + len(needle)
        if len(out) >= 20:
            break
    return out


def inspect_url(session: requests.Session, path: str) -> dict:
    url = urljoin(BASE, path)
    r = session.get(url, headers=HEADERS, timeout=25)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    scripts = []
    links = []
    for tag in soup.find_all("script"):
        src = tag.get("src")
        if src:
            scripts.append(urljoin(BASE, src))
    for tag in soup.find_all(["a", "link"]):
        href = tag.get("href")
        rel = " ".join(tag.get("rel") or []) if isinstance(tag.get("rel"), list) else str(tag.get("rel") or "")
        typ = str(tag.get("type") or "")
        text = " ".join(tag.stripped_strings)
        if href and ("rss" in (href + rel + typ + text).casefold() or "feed" in (href + rel + typ).casefold()):
            links.append({"href": urljoin(BASE, href), "rel": rel, "type": typ, "text": text})
    return {
        "url": url,
        "status": r.status_code,
        "bytes": len(r.content),
        "content_type": r.headers.get("content-type"),
        "scripts": scripts,
        "feed_links": links,
        "html_keyword_hits": {k: snippets(r.text, k, 400)[:5] for k in KEYWORDS if k.casefold() in r.text.casefold()},
    }


def inspect_script(session: requests.Session, url: str) -> dict:
    try:
        r = session.get(url, headers=HEADERS, timeout=25)
        r.raise_for_status()
        text = r.text
    except Exception as exc:
        return {"url": url, "error": str(exc)}
    hits = {}
    for key in KEYWORDS:
        if key.casefold() in text.casefold():
            hits[key] = snippets(text, key, 900)[:10]
    # Extract absolute and root-relative URL-like strings that look relevant.
    urls = set()
    for m in re.finditer(r"(?P<q>['\"])(?P<u>(?:https?://[^'\"]+|/[^'\"]{3,300}))(?P=q)", text):
        u = m.group("u")
        if any(k in u.casefold() for k in ("api", "rss", "feed", "news", "cong-bo", "article", "niemyet", "listed", "issuer")):
            urls.add(urljoin(BASE, u))
    return {
        "url": url,
        "status": r.status_code,
        "bytes": len(r.content),
        "hits": hits,
        "candidate_urls": sorted(urls)[:200],
    }


def main() -> None:
    session = requests.Session()
    pages = [inspect_url(session, path) for path in TARGETS]
    script_urls = []
    for page in pages:
        script_urls.extend(page.get("scripts", []))
    # Deduplicate and inspect same-origin JS first; cap for CI safety.
    script_urls = list(dict.fromkeys(script_urls))
    same_origin = [u for u in script_urls if "hsx.vn" in u]
    diagnostics = [inspect_script(session, u) for u in same_origin[:30]]
    print(json.dumps({
        "pages": pages,
        "script_count": len(script_urls),
        "same_origin_script_count": len(same_origin),
        "script_diagnostics": diagnostics,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
