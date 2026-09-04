#!/usr/bin/env python3
"""Fail the Pages release if production auth is incomplete, unsafe, or over-injected."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


SUPABASE_CDN = "https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"
FULL_AUTH_ASSETS = (
    "assets/auth-config.js",
    "assets/auth-email-gate.js",
    "assets/auth-policy.js",
    "assets/auth-account-security.js",
    "assets/auth.js",
    "assets/auth-extra.js",
    "assets/auth-delete-security.js",
)
HEAVY_AUTH_ASSETS = (
    "assets/auth-email-gate.js",
    "assets/auth-policy.js",
    "assets/auth-account-security.js",
    "assets/auth.js",
    "assets/auth-extra.js",
    "assets/auth-delete-security.js",
    "assets/auth.css",
    "assets/auth-extra.css",
)
HOMEPAGE_LEGACY_AUTH_UX = (
    "assets/auth-production-gate.js",
    "assets/header-auth-dedupe-v6.js",
    "assets/public-copy-v7.js",
)


def require(path: Path) -> str:
    if not path.is_file():
        raise SystemExit(f"missing required auth artifact: {path}")
    return path.read_text(encoding="utf-8")


def require_all(source: str, markers: tuple[str, ...], label: str) -> None:
    missing = [marker for marker in markers if marker not in source]
    if missing:
        raise SystemExit(f"{label} missing auth markers: {', '.join(missing)}")


def reject_all(source: str, markers: tuple[str, ...], label: str) -> None:
    present = [marker for marker in markers if marker in source]
    if present:
        raise SystemExit(f"{label} unexpectedly loads disallowed auth assets: {', '.join(present)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    args = parser.parse_args()
    site = args.site.resolve()

    config = require(site / "assets" / "auth-config.js")
    if '"configured":true' not in config:
        raise SystemExit("production auth config is not enabled")
    if '"emailDeliveryReady":true' not in config and '"emailDeliveryReady":false' not in config:
        raise SystemExit("production auth config has no explicit email-delivery launch state")
    if "https://" not in config or "supabase.co" not in config:
        raise SystemExit("production auth config has no Supabase HTTPS URL")
    if "sb_publishable_" not in config:
        raise SystemExit("production auth config is not using a publishable key")
    lowered = config.lower()
    if "sb_secret_" in lowered or "service_role" in lowered:
        raise SystemExit("privileged Supabase key detected in Pages auth config")

    required_files = [
        "assets/auth.js",
        "assets/auth-email-gate.js",
        "assets/auth-policy.js",
        "assets/auth-account-security.js",
        "assets/auth-extra.js",
        "assets/auth-delete-security.js",
        "assets/signup-link-v1.js",
        "assets/home-core-v1.js",
        "signup/index.html",
        "dang-nhap/index.html",
        "dat-lai-mat-khau/index.html",
        "tai-khoan/index.html",
        "dieu-khoan/index.html",
        "quyen-rieng-tu/index.html",
        "co-phieu/index.html",
        "index.html",
    ]
    for relative in required_files:
        require(site / relative)

    signup = require(site / "signup" / "index.html")
    signup_client = require(site / "assets" / "signup-link-v1.js")
    login = require(site / "dang-nhap" / "index.html")
    reset = require(site / "dat-lai-mat-khau" / "index.html")
    account = require(site / "tai-khoan" / "index.html")
    stock = require(site / "co-phieu" / "index.html")
    home = require(site / "index.html")
    home_core = require(site / "assets" / "home-core-v1.js")
    email_gate = require(site / "assets" / "auth-email-gate.js")
    policy = require(site / "assets" / "auth-policy.js")
    account_security = require(site / "assets" / "auth-account-security.js")
    extra = require(site / "assets" / "auth-extra.js")
    delete_security = require(site / "assets" / "auth-delete-security.js")

    checks = {
        "signup email field": ('type="email"', signup),
        "signup password field": ('type="password"', signup),
        "signup direct client": ("assets/signup-link-v1.js", signup),
        "signup edge call": ("/functions/v1/signup-link", signup_client),
        "signup automatic sign in": ("signInWithPassword", signup_client),
        "signup direct Premium continuation": ("thanh-toan/?plan=premium", signup_client),
        "terms link": ("dieu-khoan/", signup),
        "privacy link": ("quyen-rieng-tu/", signup),
        "email delivery fail-closed gate": ("emailDeliveryReady", email_gate),
        "login OTP recovery": ("data-auth-login-otp-form", login),
        "login OTP verification": ("verifyOtp", extra),
        "login OTP resend": ("auth.resend", extra),
        "consent metadata": ("terms_accepted", policy),
        "account profile": ("data-account-tier", account),
        "current password input": ('name="current_password"', account),
        "current password enforcement": ("currentPassword", account_security),
        "account deletion UI": ("data-delete-account-form", account),
        "delete password input": ('name="delete_current_password"', account),
        "delete reauthentication": ("signInWithPassword", delete_security),
        "account deletion function": ("delete-account", delete_security),
    }
    missing = [name for name, (marker, source) in checks.items() if marker not in source]
    if missing:
        raise SystemExit("auth release checks failed: " + ", ".join(missing))

    for forbidden in (
        'data-auth-signup-otp-form',
        'data-signup-email-sent',
        'autocomplete="one-time-code"',
        'Nhập mã OTP 6 số',
        'Kiểm tra email để xác minh tài khoản',
        'Đã xác minh? Đăng nhập',
        'xac-minh-email/',
        'gửi email xác minh',
    ):
        if forbidden in signup:
            raise SystemExit(f"signup verification UI leaked into production artifact: {forbidden}")

    for forbidden in ('showEmailSent', 'data-signup-email-sent', 'sr_pending_signup_email'):
        if forbidden in signup_client:
            raise SystemExit(f"legacy signup verification client leaked: {forbidden}")

    for label, source in (
        ("signup", signup),
        ("login", login),
        ("password reset", reset),
        ("account", account),
    ):
        require_all(source, FULL_AUTH_ASSETS, label)
        require_all(source, (SUPABASE_CDN, "assets/auth.css", "assets/auth-extra.css"), label)

    require_all(stock, (SUPABASE_CDN, "assets/auth-config.js", "assets/stock-api-client.js"), "stock analysis")
    reject_all(stock, HEAVY_AUTH_ASSETS, "stock analysis")

    require_all(home, ("assets/auth-config.js", "assets/home-core-v1.js"), "homepage")
    require_all(
        home_core,
        (
            "emailDeliveryReady",
            "registrationUrl",
            "leadUrl",
            "premiumUrl",
            "mountEmailLead",
            "nhan-ban-tin/",
            "thanh-toan/?plan=premium",
        ),
        "homepage core",
    )
    if SUPABASE_CDN in home:
        raise SystemExit("homepage must not load Supabase browser SDK")
    reject_all(home, (*HEAVY_AUTH_ASSETS, *HOMEPAGE_LEGACY_AUTH_UX), "homepage")

    for path in [*site.rglob("*.js"), *site.rglob("*.html")]:
        source = path.read_text(encoding="utf-8").lower()
        if "sb_secret_" in source or re.search(r"service[_-]?role\s*[:=]", source):
            raise SystemExit(f"privileged auth material detected in public artifact: {path}")

    state = "READY" if '"emailDeliveryReady":true' in config else "GATED"
    print(
        "StockRadar production auth verification: PASS "
        f"(email delivery {state}; signup creates and signs in accounts directly; auth bundles route-scoped)"
    )


if __name__ == "__main__":
    main()
