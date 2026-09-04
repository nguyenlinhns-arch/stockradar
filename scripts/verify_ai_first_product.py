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
    signup = (output / "signup" / "index.html").read_text(encoding="utf-8")
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
        "signup/?plan=free",
        "dang-ky/?plan=premium",
    ), "AI client access model", errors)

    require(signup, (
        "Free · 0đ",
        "10 câu/ngày",
        "Premium · 199.000đ/30 ngày",
        "AI không giới hạn",
        "Action Alert",
        "data-premium-email-onboarding",
        "premium-email-product-v1.css",
    ), "signup tiers", errors)

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
