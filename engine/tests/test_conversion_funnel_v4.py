from pathlib import Path
import tempfile
import unittest

from scripts import patch_conversion_funnel_v4


ROOT = Path(__file__).resolve().parents[2]


class ConversionFunnelV4Tests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_conversion_analytics_is_private_and_pii_minimal(self) -> None:
        sql = self.read("supabase/migrations/20260904073800_add_conversion_funnel_analytics.sql")
        self.assertIn("private.conversion_funnel_events", sql)
        self.assertIn("enable row level security", sql)
        self.assertIn("revoke all on table private.conversion_funnel_events from public, anon, authenticated", sql)
        self.assertIn("grant execute on function public.capture_conversion_event_v1", sql)
        self.assertIn("to service_role", sql)
        self.assertNotIn("email text", sql.lower())
        self.assertNotIn("password", sql.lower())
        self.assertNotIn("raw_ip", sql.lower())
        self.assertIn("session_hash", sql)
        self.assertIn("ip_hash", sql)

    def test_public_edge_is_origin_limited_hashes_connection_data_and_excludes_qa(self) -> None:
        edge = self.read("supabase/functions/conversion-event/index.ts")
        self.assertIn("https://stockradar.vn", edge)
        self.assertIn("ALLOWED_EVENTS", edge)
        self.assertIn("NON_PRODUCTION_ORIGINS", edge)
        self.assertIn("recorded: false", edge)
        self.assertIn("sha256Hex", edge)
        self.assertIn("SUPABASE_SERVICE_ROLE_KEY", edge)
        self.assertIn("capture_conversion_event_v1", edge)
        self.assertNotIn("p_email", edge)
        self.assertNotIn("email:", edge.lower())

    def test_browser_tracker_is_non_blocking_and_keeps_pii_out(self) -> None:
        client = self.read("website/assets/conversion-v3.js")
        for marker in (
            "/functions/v1/conversion-event",
            "credentials: 'omit'",
            "keepalive: true",
            "premium_preview_view",
            "signup_premium_view",
            "checkout_view",
            "ticker_lookup_submit",
            "sessionStorage",
        ):
            self.assertIn(marker, client)
        self.assertNotIn("payload.email", client)
        self.assertNotIn("password", client.lower())
        self.assertNotIn("otp", client.lower())

    def test_build_patch_tracks_direct_lookup_and_preserves_safe_next(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            (output / "kiem-tra-co-phieu").mkdir(parents=True)
            (output / "assets").mkdir(parents=True)
            (output / "kiem-tra-co-phieu" / "index.html").write_text(
                '<html><head></head><body><form data-stock-search-form></form></body></html>',
                encoding="utf-8",
            )
            auth = """function safeNext(value) {
  const target = new URL(value, location.href);
}
function wireSignup() {
    const form = document.querySelector('[data-auth-signup-form]');
    const otpForm = document.querySelector('[data-auth-signup-otp-form]');
    if (!form) return;
          location.href = siteUrl('tai-khoan/?verified=1');
            options: { emailRedirectTo: siteUrl('tai-khoan/?verified=1') }
          options: { emailRedirectTo: siteUrl('tai-khoan/?verified=1') }
          setMessage(message, 'Tạo tài khoản thành công. Đang mở trang tài khoản…', 'success');
          location.href = siteUrl('tai-khoan/');
}
"""
            (output / "assets" / "auth.js").write_text(auth, encoding="utf-8")

            patch_conversion_funnel_v4.inject_lookup_tracking(output)
            patch_conversion_funnel_v4.patch_auth_next(output)

            lookup = (output / "kiem-tra-co-phieu" / "index.html").read_text(encoding="utf-8")
            patched_auth = (output / "assets" / "auth.js").read_text(encoding="utf-8")
            self.assertIn("conversion-v3.js", lookup)
            self.assertIn("new URL(value, document.baseURI)", patched_auth)
            self.assertIn("const signupNext = safeNext(signupParams.get('next'));", patched_auth)
            self.assertIn("location.href = signupNext;", patched_auth)
            self.assertNotIn("emailRedirectTo: siteUrl('tai-khoan/?verified=1')", patched_auth)

    def test_privacy_policy_discloses_minimal_conversion_measurement(self) -> None:
        privacy = self.read("website/quyen-rieng-tu/index.html")
        self.assertIn("Dữ liệu kỹ thuật, đo funnel và chống lạm dụng", privacy)
        self.assertIn("không ghi email, mật khẩu, OTP, NAV", privacy)
        self.assertIn("không lưu địa chỉ IP thô", privacy)

    def test_private_business_views_report_30_day_funnel_and_ticker_interest(self) -> None:
        sql = self.read("supabase/migrations/20260904075200_add_commercial_funnel_views.sql")
        self.assertIn("private.conversion_funnel_30d_v1", sql)
        self.assertIn("home_to_lookup_pct", sql)
        self.assertIn("lookup_to_preview_pct", sql)
        self.assertIn("pricing_to_premium_signup_pct", sql)
        self.assertIn("premium_signup_to_checkout_pct", sql)
        self.assertIn("private.conversion_ticker_interest_30d_v1", sql)
        self.assertIn("premium_interest_sessions", sql)
        self.assertIn("revoke all on private.conversion_funnel_30d_v1 from public, anon, authenticated", sql)

    def test_pages_workflow_applies_conversion_funnel_patch(self) -> None:
        workflow = self.read(".github/workflows/pages.yml")
        self.assertIn("python scripts/patch_conversion_funnel_v4.py .pages-site", workflow)
        self.assertLess(
            workflow.index("patch_conversion_funnel_v4.py"),
            workflow.index("strip_public_methods.py"),
        )


if __name__ == "__main__":
    unittest.main()
