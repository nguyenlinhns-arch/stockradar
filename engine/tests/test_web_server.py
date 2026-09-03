import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

import website.server as web


class WebServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.original_db_path = web.DB_PATH
        self.original_data_dir = web.DATA_DIR
        web.DATA_DIR = Path(self.temp.name)
        web.DB_PATH = web.DATA_DIR / "web.sqlite"
        web.LOOKUP_LIMITER.clear()
        self.server = web.ThreadingHTTPServer(("127.0.0.1", 0), web.Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        web.DB_PATH = self.original_db_path
        web.DATA_DIR = self.original_data_dir
        self.temp.cleanup()

    def post(self, path: str, payload: dict[str, object]):
        request = urllib.request.Request(
            self.base + path,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        return urllib.request.urlopen(request)

    def test_pages_and_health(self) -> None:
        for path in [
            "/", "/radar5", "/breakout", "/risk", "/track-record", "/pro", "/signup",
            "/nganh", "/phan-tich", "/khuyen-nghi", "/hieu-qua", "/co-phieu/demo1", "/email",
            "/theo-doi", "/tai-khoan",
            "/kiem-tra-co-phieu", "/thay-doi-hom-nay", "/co-phieu/VCI",
            "/kien-thuc", "/kien-thuc/canslim-sepa", "/kien-thuc/vpa", "/kien-thuc/4m",
            "/kien-thuc/pocket-pivot", "/kien-thuc/cong-cu-ky-thuat",
            "/kien-thuc/quan-tri-rui-ro", "/kien-thuc/quy-trinh-stockradar", "/api/health"
        ]:
            with urllib.request.urlopen(self.base + path) as response:
                self.assertEqual(response.status, 200, path)

    def test_v212_ticker_autocomplete_quick_and_partial_report(self) -> None:
        with urllib.request.urlopen(self.base + "/api/tickers?q=H") as response:
            payload = json.load(response)
            tickers = {item["ticker"] for item in payload["items"]}
            self.assertTrue({"HPG", "HAH", "HCM", "HSG"}.issubset(tickers))
            self.assertFalse(payload["full_universe"])
        with urllib.request.urlopen(self.base + "/api/stocks/VCI/quick") as response:
            payload = json.load(response)
            self.assertEqual(payload["ticker"], "VCI")
            self.assertEqual(payload["data_status"], "BLOCKED_DATA_GATE")
        with urllib.request.urlopen(self.base + "/api/stocks/VCI/report") as response:
            self.assertEqual(response.status, 206)
            payload = json.load(response)
            self.assertIn("Đánh giá nhanh", payload["message"])

    def test_v212_invalid_ticker_and_rate_limiter(self) -> None:
        with self.assertRaises(urllib.error.HTTPError) as context:
            urllib.request.urlopen(self.base + "/api/stocks/ZZZ/quick")
        self.assertEqual(context.exception.code, 404)
        limiter = web.SlidingWindowRateLimiter()
        self.assertTrue(limiter.allow("bot", limit=2, window_seconds=60, now=1))
        self.assertTrue(limiter.allow("bot", limit=2, window_seconds=60, now=2))
        self.assertFalse(limiter.allow("bot", limit=2, window_seconds=60, now=3))
        self.assertTrue(limiter.allow("bot", limit=2, window_seconds=60, now=63))

    def test_signup_requires_consent(self) -> None:
        with self.assertRaises(urllib.error.HTTPError) as context:
            self.post("/api/signup", {"email": "qa@example.test", "proposition": "radar5"})
        self.assertEqual(context.exception.code, 400)

    def test_valid_signup_and_event(self) -> None:
        with self.post(
            "/api/signup",
            {"email": "qa@example.test", "proposition": "risk", "consent": True, "alert_opt_in": True},
        ) as response:
            self.assertEqual(response.status, 201)
        with self.post(
            "/api/events",
            {"event_name": "landing_view", "occurred_at": "2026-09-01T10:00:00Z", "session_id": "qa", "page": "/", "proposition": "organic"},
        ) as response:
            self.assertEqual(response.status, 202)


if __name__ == "__main__":
    unittest.main()
