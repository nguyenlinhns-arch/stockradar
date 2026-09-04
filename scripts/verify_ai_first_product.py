#!/usr/bin/env python3
"""Verify the production Pages artifact for the AI-first StockRadar product model."""

from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    return parser.parse_args()


def require(source: str, markers: tuple[str, ...], label: str, errors: list[str]) -> None:
    for marker in markers:
        if marker not in source:
            errors.append(f"{label}: missing {marker}")


def main() -> None:
    output = parse_args().output.resolve()
    errors: list[str] = []

    home = (output / "index.html").read_text(encoding="utf-8")
    plans = (output / "dang-ky" / "index.html").read_text(encoding="utf-8")
    signup = (output / "signup" / "index.html").read_text(encoding="utf-8")
    email_confirm = (output / "xac-minh-email" / "index.html").read_text(encoding="utf-8")
    signup_client = (output / "assets" / "signup-link-v1.js").read_text(encoding="utf-8")
    checkout = (output / "thanh-toan" / "index.html").read_text(encoding="utf-8")
    account = (output / "tai-khoan" / "index.html").read_text(encoding="utf-8")
    ai = (output / "assets" / "ai-center.js").read_text(encoding="utf-8")

    require(home, (
        "data-stockradar-ai-center",
        "StockRadar AI",
        "3 câu/ngày",
        "10 câu/ngày",
        "Hỏi không giới hạn",
        "Action Alert",
        "data-stock-search-form",
        "data-live-radar-home",
        "premium-email-product-v1.css",
    ), "AI-first homepage", errors)

    ai_pos = home.find("data-stockradar-ai-center")
    lookup_pos = home.find("data-stock-search-form")
    radar_pos = home.find("data-live-radar-home")
    if min(ai_pos, lookup_pos, radar_pos) < 0 or not (ai_pos < lookup_pos < radar_pos):
        errors.append("AI-first homepage: AI must appear before lookup and supporting Radar")

    require(ai, (
        "stock-ai-guest",
        "stock-ai",
        "KHÁCH · 3 CÂU / NGÀY",
        "FREE · 10 CÂU / NGÀY",
        "PAID · AI KHÔNG GIỚI HẠN · EMAIL ACTION ALERT",
        "dang-ky/?plan=free",
        "dang-ky/?plan=premium",
    ), "AI client access model", errors)

    require(plans, (
        "Đăng ký & thanh toán",
        "signup/?plan=premium&next=thanh-toan/%3Fplan%3Dpremium",
        "không phải đăng ký Free trước",
    ), "Premium registration entry", errors)

    require(signup, (
        "Free · 0đ",
        "10 câu/ngày",
        "Premium · 199.000đ/30 ngày",
        "AI không giới hạn",
        "Action Alert",
        "data-premium-email-onboarding",
        "premium-email-product-v1.css",
        "assets/signup-link-v1.js",
        "data-signup-email-sent",
        "gửi email xác minh",
        "Không cần nhập mã OTP",
    ), "signup tiers and email-link verification", errors)

    for forbidden in ('data-auth-signup-otp-form', 'autocomplete="one-time-code"', 'Nhập mã OTP 6 số'):
        if forbidden in signup:
            errors.append(f"signup must not expose manual OTP input: {forbidden}")

    require(signup_client, (
        "/functions/v1/signup-link",
        "event.stopImmediatePropagation()",
        "thanh-toan/?plan=premium",
        "data-signup-existing-login",
    ), "signup email-link client", errors)

    require(email_confirm, (
        "assets/email-confirm-v1.js",
        "data-email-confirm-status",
        "Không cần nhập mã OTP",
    ), "email confirmation landing", errors)

    require(checkout, (
        "StockRadar Premium",
        "199.000đ",
        "VPBank",
        "0934389822",
        "data-checkout-confirm",
        "vpbank-qr-static.svg",
    ), "Premium checkout", errors)

    require(account, (
        "data-premium-email-health",
        "data-email-health-system",
        "data-email-health-watchlist",
        "data-email-health-tickers",
        "data-email-health-last",
        'name="post_session_digest"',
        'name="weekly_report"',
        "premium-email-product-v1.css",
    ), "Premium email account health", errors)

    for private_example in ("MBB", "HPG", "ACB"):
        if private_example in ai:
            errors.append(f"AI public examples must not expose internal priority ticker: {private_example}")

    if home.count("<h1") != 1:
        errors.append("AI-first homepage must contain exactly one H1")

    if errors:
        raise RuntimeError("AI-first product verification failed:\n- " + "\n- ".join(errors))
    print("AI-first product verification: PASS")


if __name__ == "__main__":
    main()
