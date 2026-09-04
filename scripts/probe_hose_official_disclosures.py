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
    "Accept-Encoding": "identity",
}
KEYWORDS = (
    "rss", "cong-bo", "congbothongtin", "disclosure", "article", "news",
    "api/", "graphql", "odata", "search", "listed", "niemyet", "issuer",
    "staticfile", "uploads", "tin-tuc", "thong-tin-cong-bo-hose",
)


def snippets(text: str, needle: str, radius: int = 500) -> list[str]:
    out = []
    low = text.casefold(); nlow = needle.casefold(); start = 0
    while True:
        idx = low.find(nlow, start)
        if idx < 0:
            break
        out.append(text[max(0, idx-radius): min(len(text), idx+radius)])
        start = idx + len(needle)
        if len(out) >= 12:
            break
    return out


def inspect_url(session: requests.Session, path: str) -> dict:
    url = urljoin(BASE, path)
    r = session.get(url, headers=HEADERS, timeout=10)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    scripts = [urljoin(BASE, t.get("src")) for t in soup.find_all("script") if t.get("src")]
    feed_links = []
    for tag in soup.find_all(["a", "link"]):
        href = tag.get("href")
        rel = " ".join(tag.get("rel") or []) if isinstance(tag.get("rel"), list) else str(tag.get("rel") or "")
        typ = str(tag.get("type") or "")
        text = " ".join(tag.stripped_strings)
        if href and ("rss" in (href + rel + typ + text).casefold() or "feed" in (href + rel + typ).casefold()):
            feed_links.append({"href": urljoin(BASE, href), "rel": rel, "type": typ, "text": text})
    return {
        "url": url,
        "status": r.status_code,
        "bytes": len(r.content),
        "scripts": scripts,
        "feed_links": feed_links,
    }


def analyze_text(text: str) -> dict:
    hits = {k: snippets(text, k, 700)[:8] for k in KEYWORDS if k.casefold() in text.casefold()}
    urls = set()
    for m in re.finditer(r"(?P<q>['\"])(?P<u>(?:https?://[^'\"]+|/[^'\"]{3,350}))(?P=q)", text):
        u = m.group("u")
        if any(k in u.casefold() for k in ("api", "rss", "feed", "news", "cong-bo", "article", "niemyet", "listed", "issuer", "staticfile", "upload")):
            urls.add(urljoin(BASE, u))
    return {"hits": hits, "candidate_urls": sorted(urls)[:200]}


def inspect_script_ranges(session: requests.Session, url: str) -> dict:
    meta = {"url": url}
    try:
        h = session.head(url, headers=HEADERS, timeout=10, allow_redirects=True)
        meta.update({
            "head_status": h.status_code,
            "content_length": h.headers.get("content-length"),
            "accept_ranges": h.headers.get("accept-ranges"),
            "etag": h.headers.get("etag"),
            "content_type": h.headers.get("content-type"),
        })
    except Exception as exc:
        meta["head_error"] = str(exc)

    try:
        size = int(meta.get("content_length") or 0)
    except Exception:
        size = 0
    chunk = 512 * 1024
    starts = [0]
    if size > chunk * 3:
        starts.extend([max(0, size // 3 - chunk // 2), max(0, 2 * size // 3 - chunk // 2), max(0, size - chunk)])
    starts = list(dict.fromkeys(starts))
    ranges = []
    for start in starts[:4]:
        end = start + chunk - 1
        headers = {**HEADERS, "Range": f"bytes={start}-{end}"}
        try:
            r = session.get(url, headers=headers, timeout=12, stream=True)
            raw = r.raw.read(chunk, decode_content=False)
            text = raw.decode("utf-8", errors="ignore")
            ranges.append({
                "requested_range": f"{start}-{end}",
                "status": r.status_code,
                "content_range": r.headers.get("content-range"),
                "bytes_read": len(raw),
                **analyze_text(text),
            })
        except Exception as exc:
            ranges.append({"requested_range": f"{start}-{end}", "error": str(exc)})
    meta["ranges"] = ranges
    return meta


def main() -> None:
    session = requests.Session()
    pages = []
    for path in TARGETS:
        try:
            pages.append(inspect_url(session, path))
        except Exception as exc:
            pages.append({"url": urljoin(BASE, path), "error": str(exc)})
    scripts = list(dict.fromkeys(u for p in pages for u in p.get("scripts", [])))
    same_origin = [u for u in scripts if "hsx.vn" in u]
    diagnostics = [inspect_script_ranges(session, u) for u in same_origin[:3]]
    print(json.dumps({
        "pages": pages,
        "script_count": len(scripts),
        "same_origin_script_count": len(same_origin),
        "script_diagnostics": diagnostics,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
