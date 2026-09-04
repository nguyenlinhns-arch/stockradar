#!/usr/bin/env python3
"""Verify the built conversion funnel remains measurable and continuous."""

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

    required_pages = (
        "index.html",
        "kiem-tra-co-phieu/index.html",
        "co-phieu/index.html",
        "dang-ky/index.html",
        "signup/index.html",
        "hieu-qua/index.html",
        "premium-mau/index.html",
    )
    for relative in required_pages:
        path = output / relative
        if not path.is_file():
            errors.append(f"missing funnel page: {relative}")
            continue
        source = path.read_text(encoding="utf-8")
        if "conversion-v3.js" not in source:
            errors.append(f"conversion tracker missing: {relative}")

    # Checkout is intentionally absent from the production artifact while the
    # billing gate is closed. If it is present in a future ready build, it must
    # participate in the same privacy-minimal funnel measurement.
    checkout_path = output / "thanh-toan" / "index.html"
    if checkout_path.is_file():
        checkout = checkout_path.read_text(encoding="utf-8")
        if "conversion-v3.js" not in checkout:
            errors.append("conversion tracker missing: thanh-toan/index.html")

    tracker_path = output / "assets" / "conversion-v3.js"
    if not tracker_path.is_file():
        errors.append("conversion-v3.js missing")
    else:
        tracker = tracker_path.read_text(encoding="utf-8")
        require(
            tracker,
            (
                "/functions/v1/conversion-event",
                "premium_preview_view",
                "premium_sample_view",
                "pricing_view",
                "signup_premium_view",
                "checkout_view",
                "ticker_lookup_submit",
                "credentials: 'omit'",
                "keepalive: true",
            ),
            "conversion tracker",
            errors,
        )
        for forbidden in ("payload.email", "password", "authorization", "broker_account", "nav_value"):
            if forbidden.lower() in tracker.lower():
                errors.append(f"conversion tracker contains PII/sensitive marker: {forbidden}")

    auth_path = output / "assets" / "auth.js"
    if not auth_path.is_file():
        errors.append("auth.js missing")
    else:
        auth = auth_path.read_text(encoding="utf-8")
        require(
            auth,
            (
                "new URL(value, document.baseURI)",
                "const signupNext = safeNext(signupParams.get('next'));",
                "options: { emailRedirectTo: signupNext }",
                "location.href = signupNext;",
            ),
            "Premium next-step",
            errors,
        )
        if "new URL(value, location.href)" in auth:
            errors.append("safeNext still resolves against /signup/ instead of site base")

    privacy_path = output / "quyen-rieng-tu" / "index.html"
    if privacy_path.is_file():
        privacy = privacy_path.read_text(encoding="utf-8")
        require(
            privacy,
            (
                "đo funnel",
                "không ghi email, mật khẩu, OTP, NAV",
                "không lưu địa chỉ IP thô",
            ),
            "privacy policy",
            errors,
        )
    else:
        errors.append("privacy page missing")

    if errors:
        raise RuntimeError("Conversion funnel v4 verification failed:\n- " + "\n- ".join(errors))

    checkout_state = "tracked" if checkout_path.is_file() else "fail-closed"
    print(
        "Conversion funnel v4 verification: PASS "
        f"(tracked lookup → Premium → signup → safe next; checkout={checkout_state})"
    )


if __name__ == "__main__":
    main()
