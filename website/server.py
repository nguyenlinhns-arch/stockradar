from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sqlite3
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from engine.stockradar.ticker_lookup import TickerMaster, UnsupportedTickerError


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "stockradar_web.sqlite"
MAX_BODY = 16_384
TICKER_MASTER_PATH = ROOT / "public" / "data" / "ticker-universe.json"
STOCK_REPORT_PATH = ROOT / "public" / "data" / "stock-reports.json"
ANON_LOOKUP_LIMIT = int(os.environ.get("STOCKRADAR_ANON_LOOKUP_LIMIT", "30"))
ANON_LOOKUP_WINDOW_SECONDS = int(os.environ.get("STOCKRADAR_ANON_LOOKUP_WINDOW_SECONDS", "3600"))
ALLOWED_EVENTS = {
    "ad_click", "landing_view", "radar_view", "top5_expand", "track_record_view",
    "signup_started", "signup_completed", "alert_opt_in", "pro_page_view",
    "trial_started", "subscription_started", "return_d1", "return_d7",
    "knowledge_view", "method_view", "horizon_select", "stock_search",
    "stock_report_view", "top10_view", "watchlist_add", "email_view",
    "checkout_started", "payment_completed",
    "top_view", "horizon_change", "sector_view", "recommendation_list_view",
    "performance_view", "sample_premium_report_view", "signup_start",
    "signup_complete", "pro_view", "checkout_start", "payment_complete",
    "email_open", "email_click", "renewal_complete",
    "ticker_search", "four_horizon_view", "holding_view", "recommendation_public_view",
    "recommendation_history_view", "today_changes_view", "benchmark_view",
    "onboarding_horizon_selected", "onboarding_sector_selected", "onboarding_ticker_added",
    "paid_email_preference_changed", "ticker_input_started", "ticker_autocomplete_selected",
    "ticker_search_submitted", "ticker_search_valid", "ticker_search_invalid",
    "ticker_cache_hit", "ticker_cache_miss", "quick_report_view", "full_report_requested",
    "report_generation_completed", "report_generation_failed", "ticker_trial_cta_clicked",
    "ticker_watch_started"
}


class SlidingWindowRateLimiter:
    def __init__(self):
        self._events: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str, *, limit: int, window_seconds: int, now: float | None = None) -> bool:
        current = time.monotonic() if now is None else now
        cutoff = current - window_seconds
        with self._lock:
            recent = [value for value in self._events.get(key, []) if value > cutoff]
            if len(recent) >= limit:
                self._events[key] = recent
                return False
            recent.append(current)
            self._events[key] = recent
            return True

    def clear(self) -> None:
        with self._lock:
            self._events.clear()


LOOKUP_LIMITER = SlidingWindowRateLimiter()


def load_ticker_master() -> TickerMaster:
    return TickerMaster.from_path(TICKER_MASTER_PATH)


def load_stock_reports() -> dict[str, dict[str, object]]:
    payload = json.loads(STOCK_REPORT_PATH.read_text(encoding="utf-8"))
    return {str(item["ticker"]): item for item in payload.get("items", [])}
PROPOSITIONS = {
    "radar5", "breakout", "risk", "organic", "horizon-top", "ticker-search",
    "recommendation-history", "performance", "stock-report", "email-alert", "account"
}


def connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS leads (
            lead_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            contact TEXT NOT NULL,
            contact_type TEXT NOT NULL,
            proposition TEXT NOT NULL,
            investor_profile TEXT,
            requested_tier TEXT NOT NULL DEFAULT 'FREE',
            preferences_json TEXT NOT NULL DEFAULT '{}',
            product_email_consent INTEGER NOT NULL DEFAULT 0,
            alert_opt_in INTEGER NOT NULL,
            consent INTEGER NOT NULL,
            utm_json TEXT NOT NULL
        );
        CREATE UNIQUE INDEX IF NOT EXISTS lead_contact_proposition
            ON leads(contact, proposition);
        CREATE TABLE IF NOT EXISTS analytics_events (
            event_id TEXT PRIMARY KEY,
            occurred_at TEXT NOT NULL,
            received_at TEXT NOT NULL,
            event_name TEXT NOT NULL,
            session_id TEXT NOT NULL,
            page TEXT NOT NULL,
            proposition TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS ticker_search_log (
            search_id TEXT PRIMARY KEY,
            searched_at TEXT NOT NULL,
            ticker TEXT NOT NULL,
            session_id TEXT,
            source TEXT NOT NULL,
            campaign TEXT,
            result_status TEXT NOT NULL
        );
        """
    )
    return connection


def safe_text(value: object, limit: int = 240) -> str:
    return str(value or "").strip()[:limit]


def safe_list(value: object, *, limit: int = 3, item_limit: int = 40) -> list[str]:
    if not isinstance(value, list):
        return []
    return [safe_text(item, item_limit) for item in value[:limit] if safe_text(item, item_limit)]


class Handler(BaseHTTPRequestHandler):
    server_version = "StockRadarMVP/2.1.2"

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}")

    def send_json(self, payload: dict[str, object], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.security_headers()
        self.end_headers()
        self.wfile.write(body)

    def security_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; connect-src 'self'; base-uri 'self'; form-action 'self'"
        )

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/health":
            return self.send_json({"status": "ok", "service": "stockradar-mvp", "version": "2.1.2"})
        if path == "/api/tickers":
            return self.handle_ticker_autocomplete(parse_qs(parsed.query).get("q", [""])[0])
        if path.startswith("/api/stocks/"):
            parts = [part for part in path.split("/") if part]
            if len(parts) == 4 and parts[:2] == ["api", "stocks"]:
                return self.handle_stock_lookup(parts[2], parts[3])
        self.serve_static(path)

    def lookup_allowed(self) -> bool:
        key = f"{self.client_address[0]}:ticker-lookup"
        if LOOKUP_LIMITER.allow(
            key,
            limit=ANON_LOOKUP_LIMIT,
            window_seconds=ANON_LOOKUP_WINDOW_SECONDS,
        ):
            return True
        self.send_json(
            {"error": "RATE_LIMITED", "message": "Bạn đã tra cứu quá nhanh. Vui lòng thử lại sau."},
            HTTPStatus.TOO_MANY_REQUESTS,
        )
        return False

    def handle_ticker_autocomplete(self, query: str) -> None:
        if not self.lookup_allowed():
            return
        master = load_ticker_master()
        items = [item.to_dict() for item in master.autocomplete(query)]
        self.send_json(
            {
                "items": items,
                "snapshot_id": master.snapshot_id,
                "full_universe": master.full_universe,
                "data_grade": master.data_grade,
            }
        )

    def handle_stock_lookup(self, ticker: str, report_type: str) -> None:
        if report_type not in {"quick", "report"}:
            return self.send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
        if not self.lookup_allowed():
            return
        master = load_ticker_master()
        try:
            security = master.resolve(ticker)
        except UnsupportedTickerError as error:
            return self.send_json(
                {"error": "UNSUPPORTED_TICKER", "message": str(error)},
                HTTPStatus.NOT_FOUND,
            )
        report = load_stock_reports().get(security.ticker)
        if report is None:
            return self.send_json(
                {
                    "ticker": security.ticker,
                    "company_name": security.company_name,
                    "sector": security.sector,
                    "data_status": "INSUFFICIENT",
                    "message": "Đánh giá nhanh đã sẵn sàng. Một số phần phân tích chuyên sâu hiện chưa đủ dữ liệu.",
                }
            )
        if report_type == "report" and not bool(report.get("deep_report_available")):
            return self.send_json(
                {
                    **report,
                    "message": "Đánh giá nhanh đã sẵn sàng. Một số phần phân tích chuyên sâu hiện chưa đủ dữ liệu.",
                },
                HTTPStatus.PARTIAL_CONTENT,
            )
        self.send_json(report)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path not in {"/api/signup", "/api/events"}:
            return self.send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > MAX_BODY:
            return self.send_json({"error": "Invalid request size"}, HTTPStatus.BAD_REQUEST)
        try:
            payload = json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return self.send_json({"error": "Invalid JSON"}, HTTPStatus.BAD_REQUEST)
        if path == "/api/signup":
            return self.handle_signup(payload)
        return self.handle_event(payload)

    def handle_signup(self, payload: dict[str, object]) -> None:
        email = safe_text(payload.get("email"), 160).lower()
        phone = safe_text(payload.get("phone"), 30)
        contact = email or phone
        contact_type = "email" if email else "phone"
        proposition = safe_text(payload.get("proposition"), 30) or "organic"
        consent = bool(payload.get("consent"))
        requested_tier = safe_text(payload.get("requested_tier"), 12).upper() or "FREE"
        if requested_tier not in {"FREE", "TRIAL"}:
            return self.send_json({"error": "Gói khởi đầu không hợp lệ"}, HTTPStatus.BAD_REQUEST)
        if not contact:
            return self.send_json({"error": "Cần email hoặc số điện thoại"}, HTTPStatus.BAD_REQUEST)
        if proposition not in PROPOSITIONS:
            return self.send_json({"error": "Proposition không hợp lệ"}, HTTPStatus.BAD_REQUEST)
        if not consent:
            return self.send_json({"error": "Cần đồng ý cho StockRadar liên hệ"}, HTTPStatus.BAD_REQUEST)
        lead_id = str(uuid.uuid4())
        try:
            with connect() as connection:
                connection.execute(
                    """
                    INSERT INTO leads (
                        lead_id, created_at, contact, contact_type, proposition,
                        investor_profile, requested_tier, preferences_json,
                        product_email_consent, alert_opt_in, consent, utm_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        lead_id, datetime.now(timezone.utc).isoformat(), contact, contact_type,
                        proposition, safe_text(payload.get("investor_profile"), 80), requested_tier,
                        json.dumps({
                            "horizons": safe_list(payload.get("preferred_horizons"), limit=4),
                            "sectors": safe_list(payload.get("preferred_sectors")),
                            "tickers": safe_list(payload.get("watch_tickers"), item_limit=12),
                        }, ensure_ascii=False),
                        1 if requested_tier == "TRIAL" and email and payload.get("product_email_consent") else 0,
                        1 if requested_tier == "TRIAL" and email and payload.get("alert_opt_in") else 0,
                        1,
                        json.dumps(payload.get("utm") or {}, ensure_ascii=False)
                    )
                )
        except sqlite3.IntegrityError:
            return self.send_json({"status": "already_registered"}, HTTPStatus.OK)
        self.send_json({"status": "created", "lead_id": lead_id}, HTTPStatus.CREATED)

    def handle_event(self, payload: dict[str, object]) -> None:
        name = safe_text(payload.get("event_name"), 60)
        if name not in ALLOWED_EVENTS:
            return self.send_json({"error": "Event not allowed"}, HTTPStatus.BAD_REQUEST)
        with connect() as connection:
            connection.execute(
                """
                INSERT INTO analytics_events (
                    event_id, occurred_at, received_at, event_name, session_id,
                    page, proposition, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()), safe_text(payload.get("occurred_at"), 60),
                    datetime.now(timezone.utc).isoformat(), name,
                    safe_text(payload.get("session_id"), 100), safe_text(payload.get("page"), 200),
                    safe_text(payload.get("proposition"), 30),
                    json.dumps(payload, ensure_ascii=False)
                )
            )
        self.send_json({"status": "accepted"}, HTTPStatus.ACCEPTED)

    def serve_static(self, requested_path: str) -> None:
        route = requested_path.rstrip("/")
        if route == "":
            candidate = ROOT / "index.html"
        elif route.startswith("/co-phieu/") and (ROOT / "co-phieu" / "index.html").is_file():
            candidate = ROOT / "co-phieu" / "index.html"
        elif (ROOT / route.lstrip("/") / "index.html").is_file():
            candidate = ROOT / route.lstrip("/") / "index.html"
        else:
            candidate = (ROOT / requested_path.lstrip("/")).resolve()
        try:
            candidate.relative_to(ROOT)
        except ValueError:
            return self.send_error(HTTPStatus.FORBIDDEN)
        if not candidate.is_file():
            return self.send_error(HTTPStatus.NOT_FOUND)
        mime, _ = mimetypes.guess_type(candidate.name)
        body = candidate.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", (mime or "application/octet-stream") + ("; charset=utf-8" if (mime or "").startswith("text/") or mime in {"application/javascript", "application/json"} else ""))
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store" if candidate.suffix == ".json" else "public, max-age=300")
        self.security_headers()
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve StockRadar MVP")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    connect().close()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"StockRadar MVP running at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
