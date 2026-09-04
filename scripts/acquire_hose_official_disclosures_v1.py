#!/usr/bin/env python3
from __future__ import annotations

import argparse
import concurrent.futures as cf
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import re
import time
from urllib.parse import urlencode

import pandas as pd
import requests

EXPECTED_HOSE = 405
LISTING_API = "https://api.hsx.vn/l/api/v1/1"
NEWS_API = "https://api.hsx.vn/n/api/v1/1"
MEDIA_API = "https://api.hsx.vn/m/api/v1/1"
STATIC_BASE = "https://staticfile.hsx.vn/"
HEADERS = {
    "User-Agent": "StockRadar-Internal-Research/1.0",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.7",
    "Origin": "https://www.hsx.vn",
    "Referer": "https://www.hsx.vn/",
}

KEYWORDS = {
    "EARNINGS": ("kết quả kinh doanh", "báo cáo tài chính", "bctc", "lợi nhuận", "doanh thu", "lãi ròng", "ước lợi nhuận", "kqkd"),
    "CAPACITY": ("nhà máy", "công suất", "khởi công", "vận hành", "mở rộng", "dây chuyền", "dự án"),
    "MA_CONSOLIDATION": ("sáp nhập", "mua lại", "m&a", "thoái vốn", "chuyển nhượng", "thâu tóm"),
    "MAJOR_CONTRACT": ("trúng thầu", "hợp đồng", "đơn hàng", "gói thầu"),
    "POLICY_INDUSTRY": ("chính sách", "nghị định", "thuế", "hạn ngạch", "quota", "giá bán", "điều chỉnh giá"),
    "INSIDER": ("người nội bộ", "người có liên quan", "giao dịch cổ phiếu", "giao dịch quyền mua"),
    "CAPITAL_ACTION": ("cổ tức", "phát hành", "chào bán", "quyền mua", "esop", "chia cổ phiếu", "thưởng cổ phiếu", "ngày đăng ký cuối cùng", "ngày đkcc"),
    "LISTING_STATUS": ("hủy niêm yết", "tạm ngừng giao dịch", "đình chỉ giao dịch", "thay đổi niêm yết", "thay đổi đăng ký niêm yết", "niêm yết bổ sung", "tình trạng chứng khoán", "cảnh báo", "kiểm soát", "hạn chế giao dịch"),
    "GOVERNANCE": ("bổ nhiệm", "miễn nhiệm", "chủ tịch", "tổng giám đốc", "hđqt", "đhđcđ", "đại hội đồng cổ đông", "lấy ý kiến cổ đông"),
}


def normalize_ticker(value: object) -> str:
    return str(value or "").strip().upper()


def classify(title: str) -> str:
    value = str(title or "").casefold()
    for category, terms in KEYWORDS.items():
        if any(term in value for term in terms):
            return category
    return "OTHER"


def _get_json(session: requests.Session, url: str, retries: int = 3) -> dict:
    last = None
    for attempt in range(retries):
        try:
            response = session.get(url, headers=HEADERS, timeout=18)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict) or payload.get("success") is not True:
                raise RuntimeError("HOSE API returned unsuccessful envelope")
            data = payload.get("data")
            return data if isinstance(data, dict) else {}
        except Exception as exc:
            last = exc
            time.sleep(min(3.0, 0.4 * (2**attempt)))
    raise RuntimeError(f"HOSE API fetch failed: {url}: {last}")


def lookup_security_id(session: requests.Session, ticker: str) -> int:
    query = urlencode({"code": ticker})
    data = _get_json(session, f"{LISTING_API}/securities/stock?{query}")
    for item in data.get("list") or []:
        if normalize_ticker(item.get("code")) == ticker:
            try:
                sid = int(item.get("id") or 0)
            except Exception:
                sid = 0
            if sid > 0:
                return sid
    return 0


def list_news(session: requests.Session, security_id: int, start: date, end: date) -> list[dict]:
    rows: list[dict] = []
    page = 1
    while True:
        query = urlencode({
            "pageIndex": page,
            "pageSize": 20,
            "startDate": start.isoformat(),
            "endDate": end.isoformat(),
        })
        data = _get_json(session, f"{NEWS_API}/news/securities/{security_id}/1?{query}")
        items = data.get("list") or []
        rows.extend(x for x in items if isinstance(x, dict))
        paging = data.get("paging") or {}
        try:
            total_pages = int(paging.get("totalPages") or 0)
        except Exception:
            total_pages = 0
        if not items or total_pages <= page:
            break
        page += 1
        if page > 100:
            raise RuntimeError(f"HOSE news pagination exceeded safety cap for security {security_id}")
    return rows


def list_media(session: requests.Session, news_id: int) -> list[dict]:
    data = _get_json(session, f"{MEDIA_API}/mediafiles/1/{news_id}?pageIndex=1&pageSize=100&year=0")
    return [x for x in (data.get("list") or []) if isinstance(x, dict)]


def posted_iso(value: object) -> str | None:
    try:
        ts = int(value)
    except Exception:
        return None
    if ts <= 0:
        return None
    try:
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    except Exception:
        return None


def static_url(item: dict) -> str | None:
    path = str(item.get("filePath") or "").strip()
    if path.startswith("~/"):
        path = path[2:]
    path = path.lstrip("/")
    if not path:
        return None
    return STATIC_BASE + path


def fetch_ticker(ticker: str, start: date, end: date, include_media_days: int) -> tuple[str, int, list[dict], str | None]:
    session = requests.Session()
    try:
        sid = lookup_security_id(session, ticker)
        if sid <= 0:
            return ticker, 0, [], "SECURITY_ID_NOT_FOUND"
        news = list_news(session, sid, start, end)
        now = datetime.now(timezone.utc)
        out = []
        for item in news:
            try:
                news_id = int(item.get("id") or 0)
            except Exception:
                news_id = 0
            title = str(item.get("title") or "").strip()
            updated_at = posted_iso(item.get("postedDate"))
            media_urls: list[str] = []
            if news_id > 0 and updated_at:
                try:
                    age_days = (now - datetime.fromisoformat(updated_at)).days
                except Exception:
                    age_days = 9999
                if age_days <= include_media_days:
                    try:
                        media_urls = [u for u in (static_url(x) for x in list_media(session, news_id)) if u]
                    except Exception:
                        media_urls = []
            out.append({
                "ticker": ticker,
                "security_id": sid,
                "news_id": news_id,
                "title": title,
                "category": classify(title),
                "updated_at": updated_at,
                "source": "HOSE_OFFICIAL_API",
                "source_url": f"https://www.hsx.vn/vi/quan-ly-niem-yet/{ticker.lower()}",
                "attachment_count": len(media_urls),
                "attachment_urls": json.dumps(media_urls, ensure_ascii=False),
            })
        return ticker, sid, out, None
    except Exception as exc:
        return ticker, 0, [], str(exc)
    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Acquire official HOSE issuer disclosures for internal StockRadar catalyst verification.")
    parser.add_argument("--universe", required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--lookback-days", type=int, default=120)
    parser.add_argument("--include-media-days", type=int, default=45)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    universe = pd.read_csv(args.universe)
    if "ticker" not in universe.columns:
        raise SystemExit("universe missing ticker")
    tickers = sorted(set(universe["ticker"].astype(str).str.strip().str.upper()))
    if len(tickers) != EXPECTED_HOSE:
        raise SystemExit(f"canonical HOSE must contain {EXPECTED_HOSE} tickers, got {len(tickers)}")

    as_of = date.fromisoformat(args.as_of)
    lookback = max(30, min(int(args.lookback_days), 370))
    start = as_of - timedelta(days=lookback)
    workers = max(1, min(int(args.workers), 12))
    media_days = max(0, min(int(args.include_media_days), lookback))

    rows: list[dict] = []
    status_rows: list[dict] = []
    with cf.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(fetch_ticker, ticker, start, as_of, media_days) for ticker in tickers]
        for future in cf.as_completed(futures):
            ticker, sid, ticker_rows, error = future.result()
            status_rows.append({
                "ticker": ticker,
                "security_id": sid,
                "query_ok": error is None,
                "row_count": len(ticker_rows),
                "error": error,
            })
            if error is None:
                rows.extend(ticker_rows)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    status = pd.DataFrame(status_rows).sort_values("ticker")
    status.to_csv(out_dir / "hose_official_disclosures_coverage_405.csv", index=False, encoding="utf-8-sig")

    history = pd.DataFrame(rows)
    if history.empty:
        history = pd.DataFrame(columns=["ticker", "security_id", "news_id", "title", "category", "updated_at", "source", "source_url", "attachment_count", "attachment_urls"])
    else:
        history["ticker"] = history["ticker"].astype(str).str.strip().str.upper()
        history = history.drop_duplicates(subset=["ticker", "news_id", "title"]).sort_values(["updated_at", "ticker"], ascending=[False, True])
    history.to_csv(out_dir / "hose_official_disclosures_history.csv", index=False, encoding="utf-8-sig")

    query_ok = int(status["query_ok"].fillna(False).astype(bool).sum())
    coverage_ratio = query_ok / EXPECTED_HOSE
    latest = None
    if not history.empty:
        dt = pd.to_datetime(history["updated_at"], errors="coerce", utc=True)
        if dt.notna().any():
            latest = dt.max().isoformat()
    tickers_with_rows = int(history["ticker"].nunique()) if not history.empty else 0
    recent30_tickers = 0
    if not history.empty:
        dt = pd.to_datetime(history["updated_at"], errors="coerce", utc=True)
        cutoff = pd.Timestamp(as_of - timedelta(days=30), tz="UTC")
        recent30_tickers = int(history.loc[dt >= cutoff, "ticker"].nunique())

    source_ready = bool(coverage_ratio >= 0.98 and len(history) > 0 and latest is not None)
    manifest = {
        "schema_version": "STOCKRADAR_HOSE_OFFICIAL_DISCLOSURES_V1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "as_of": as_of.isoformat(),
        "window_start": start.isoformat(),
        "window_end": as_of.isoformat(),
        "canonical_hose": EXPECTED_HOSE,
        "ticker_queries_ok": query_ok,
        "ticker_query_coverage_ratio": coverage_ratio,
        "row_count": int(len(history)),
        "tickers_with_rows": tickers_with_rows,
        "tickers_with_rows_30d": recent30_tickers,
        "latest_updated_at": latest,
        "source_ready_internal": source_ready,
        "source": "HOSE_OFFICIAL_API",
        "source_hosts": ["api.hsx.vn", "staticfile.hsx.vn", "www.hsx.vn"],
        "catalyst_alpha_weight_allowed": False,
        "publication_allowed": False,
        "policy": "Official HOSE disclosures are verification/context evidence. They do not enable catalyst alpha or public publication by themselves.",
    }
    (out_dir / "hose_official_disclosures_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))


if __name__ == "__main__":
    main()
