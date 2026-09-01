from __future__ import annotations

import argparse
import json
import mimetypes
import sqlite3
import uuid
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "stockradar_web.sqlite"
MAX_BODY = 16_384
ALLOWED_EVENTS = {
    "ad_click", "landing_view", "radar_view", "top5_expand", "track_record_view",
    "signup_started", "signup_completed", "alert_opt_in", "pro_page_view",
    "trial_started", "subscription_started", "return_d1", "return_d7",
    "knowledge_view", "method_view", "horizon_select", "stock_search",
    "stock_report_view", "top10_view", "watchlist_add", "email_view",
    "checkout_started", "payment_completed"
}
PROPOSITIONS = {"radar5", "breakout", "risk", "organic"}


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
        """
    )
    return connection


def safe_text(value: object, limit: int = 240) -> str:
    return str(value or "").strip()[:limit]


class Handler(BaseHTTPRequestHandler):
    server_version = "StockRadarMVP/1.0"

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
        path = urlparse(self.path).path
        if path == "/api/health":
            return self.send_json({"status": "ok", "service": "stockradar-mvp"})
        self.serve_static(path)

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
                        investor_profile, alert_opt_in, consent, utm_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        lead_id, datetime.now(timezone.utc).isoformat(), contact, contact_type,
                        proposition, safe_text(payload.get("investor_profile"), 80),
                        1 if payload.get("alert_opt_in") else 0, 1,
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
