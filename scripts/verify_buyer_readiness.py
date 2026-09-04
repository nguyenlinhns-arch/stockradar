#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    return parser.parse_args()


def main() -> None:
    output = parse_args().output.resolve()
    errors: list[str] = []

    top_path = output / "public" / "data" / "top-stocks.json"
    if not top_path.is_file():
        errors.append("top-stocks.json missing")
    else:
        payload = json.loads(top_path.read_text(encoding="utf-8"))
        valid = payload.get("ranking_valid") is True
        strongest = payload.get("strongest") or []
        by_sector = payload.get("by_sector") or []
        computation = payload.get("computation") or {}
        if valid and not strongest:
            errors.append("valid Top HOSE ranking cannot be empty")
        if not valid and (strongest or by_sector):
            errors.append("invalid Top HOSE ranking must publish zero ranked rows")
        if valid and payload.get("gate", {}).get("passed") is not True:
            errors.append("ranking_valid requires passed gate")
        if computation.get("calculation_origin") != "STOCKRADAR_ENGINE":
            errors.append("Top HOSE calculation origin must be STOCKRADAR_ENGINE")
        if computation.get("external_input_role") != "RAW_INPUT_ONLY":
            errors.append("Top HOSE external input role must be RAW_INPUT_ONLY")
        if computation.get("external_scores_accepted") is not False:
            errors.append("Top HOSE must reject all external scores/rankings/signals")
        for item in strongest:
            if item.get("calculated_by") != "STOCKRADAR_ENGINE":
                errors.append(f"ranked item not StockRadar-computed: {item.get('ticker')}")

    home = output / "index.html"
    if not home.is_file():
        errors.append("homepage missing")
    else:
        source = home.read_text(encoding="utf-8")
        for marker in ("buyer-readiness-v1.css", "buyer-readiness-v1.js", "checkoutReady:true", "emailDeliveryReady:false"):
            if marker not in source:
                errors.append(f"homepage buyer marker missing: {marker}")
        for forbidden in (
            "TOP CỔ PHIẾU KHUYẾN NGHỊ CỦA STOCKRADAR",
            "Nhận email 09:00",
            "Nhận bản tin 09:00 miễn phí",
            "home-lead-form",
        ):
            if forbidden.lower() in source.lower():
                errors.append(f"inactive/misleading homepage promise remains: {forbidden}")

    checkout = output / "thanh-toan" / "index.html"
    if not checkout.is_file():
        errors.append("checkout route missing from buyer journey")
    else:
        checkout_source = checkout.read_text(encoding="utf-8")
        for marker in (
            "VietQR",
            "data-checkout-confirm",
            "data-checkout-account-email",
            "assets/checkout-v1.js",
            "assets/auth-config.js",
            "199.000đ",
            "Không tự gia hạn",
        ):
            if marker not in checkout_source:
                errors.append(f"checkout marker missing: {marker}")

    signup = output / "signup" / "index.html"
    auth_js = output / "assets" / "auth.js"
    if not signup.is_file() or not auth_js.is_file():
        errors.append("signup continuation artifacts missing")
    else:
        signup_source = signup.read_text(encoding="utf-8")
        auth_source = auth_js.read_text(encoding="utf-8")
        if 'value="premium"' not in signup_source:
            errors.append("Premium signup option missing")
        for marker in ("PENDING_SIGNUP_PLAN_KEY", "thanh-toan/?plan=premium", "pendingSignupDestination"):
            if marker not in auth_source:
                errors.append(f"Premium signup continuation missing: {marker}")

    for page in output.rglob("*.html"):
        source = page.read_text(encoding="utf-8")
        if "buyer-readiness-v1.js" not in source:
            errors.append(f"buyer runtime missing: {page.relative_to(output)}")

    buyer_js = output / "assets" / "buyer-readiness-v1.js"
    if not buyer_js.is_file():
        errors.append("buyer-readiness-v1.js missing")
    else:
        source = buyer_js.read_text(encoding="utf-8")
        for marker in (
            "Top cổ phiếu HOSE theo tiêu chí StockRadar.vn",
            "Top mạnh nhất",
            "Top theo ngành",
            "Danh sách cổ phiếu theo Radar rà soát",
            "DECISION CARD",
            "StockRadar Score",
            "Xếp hạng HOSE",
            "Buy Zone",
            "Risk/Reward",
            "checkoutReady",
        ):
            if marker not in source:
                errors.append(f"buyer product marker missing: {marker}")

    if errors:
        raise RuntimeError("Buyer-readiness verification failed:\n- " + "\n- ".join(errors))
    print("StockRadar buyer-readiness verification: PASS (signup-first Premium checkout published; product email remains gated)")


if __name__ == "__main__":
    main()
