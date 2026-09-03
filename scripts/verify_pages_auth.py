#!/usr/bin/env python3
"""Fail the Pages release if production auth is incomplete or unsafe."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


def require(path: Path) -> str:
    if not path.is_file():
        raise SystemExit(f"missing required auth artifact: {path}")
    return path.read_text(encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    args = parser.parse_args()
    site = args.site.resolve()

    config = require(site / "assets" / "auth-config.js")
    if '"configured":true' not in config:
        raise SystemExit("production auth config is not enabled")
    if "https://" not in config or "supabase.co" not in config:
        raise SystemExit("production auth config has no Supabase HTTPS URL")
    if "sb_publishable_" not in config:
        raise SystemExit("production auth config is not using a publishable key")
    lowered = config.lower()
    if "sb_secret_" in lowered or "service_role" in lowered:
        raise SystemExit("privileged Supabase key detected in Pages auth config")

    required_files = [
        "assets/auth.js",
        "assets/auth-policy.js",
        "assets/auth-account-security.js",
        "assets/auth-extra.js",
        "assets/auth-delete-security.js",
        "signup/index.html",
        "dang-nhap/index.html",
        "dat-lai-mat-khau/index.html",
        "tai-khoan/index.html",
        "dieu-khoan/index.html",
        "quyen-rieng-tu/index.html",
    ]
    for relative in required_files:
        require(site / relative)

    signup = require(site / "signup" / "index.html")
    login = require(site / "dang-nhap" / "index.html")
    account = require(site / "tai-khoan" / "index.html")
    auth = require(site / "assets" / "auth.js")
    policy = require(site / "assets" / "auth-policy.js")
    account_security = require(site / "assets" / "auth-account-security.js")
    extra = require(site / "assets" / "auth-extra.js")
    delete_security = require(site / "assets" / "auth-delete-security.js")

    checks = {
        "signup OTP input": ("one-time-code", signup),
        "signup OTP form": ("data-auth-signup-otp-form", signup),
        "terms link": ("dieu-khoan/", signup),
        "privacy link": ("quyen-rieng-tu/", signup),
        "login OTP recovery": ("data-auth-login-otp-form", login),
        "OTP verification": ("verifyOtp", auth + extra),
        "OTP resend": ("auth.resend", auth + extra),
        "consent metadata": ("terms_accepted", policy),
        "account profile": ("data-account-tier", account),
        "current password input": ("name=\"current_password\"", account),
        "current password enforcement": ("currentPassword", account_security),
        "account deletion UI": ("data-delete-account-form", account),
        "delete password input": ("name=\"delete_current_password\"", account),
        "delete reauthentication": ("signInWithPassword", delete_security),
        "account deletion function": ("delete-account", delete_security),
    }
    missing = [name for name, (marker, source) in checks.items() if marker not in source]
    if missing:
        raise SystemExit("auth release checks failed: " + ", ".join(missing))

    # Every deployed HTML page should receive the same public auth bundle when auth is enabled.
    sample_pages = [site / "index.html", site / "signup" / "index.html", site / "dang-nhap" / "index.html"]
    bundle = (
        "assets/auth-config.js",
        "assets/auth-policy.js",
        "assets/auth-account-security.js",
        "assets/auth.js",
        "assets/auth-extra.js",
        "assets/auth-delete-security.js",
    )
    for page in sample_pages:
        source = require(page)
        for asset in bundle:
            if asset not in source:
                raise SystemExit(f"{page} missing injected auth asset {asset}")

    # Reject obvious accidental embedding of privileged key names in public JavaScript/HTML.
    for path in [*site.rglob("*.js"), *site.rglob("*.html")]:
        source = path.read_text(encoding="utf-8").lower()
        if "sb_secret_" in source or re.search(r"service[_-]?role\s*[:=]", source):
            raise SystemExit(f"privileged auth material detected in public artifact: {path}")

    print("StockRadar production auth verification: PASS")


if __name__ == "__main__":
    main()
