#!/usr/bin/env python3
"""Patch the built Pages artifact for a continuous Premium buyer journey.

Goals:
- direct /kiem-tra-co-phieu/ visits use the same privacy-minimal conversion tracker;
- safe `next` URLs resolve from the site base, not from /signup/;
- legacy Premium signup/OTP flows return to a requested same-origin next step;
- the completed signup flow may already preserve Free/Premium destination itself;
- no data, email, or billing gate is opened by this patch.
"""

from __future__ import annotations

import argparse
from pathlib import Path


CONVERSION_ASSETS = (
    '<link rel="stylesheet" href="assets/conversion-v3.css?v=20260904-conv3" data-conversion-v3>\n'
    '<script src="assets/conversion-v3.js?v=20260904-conv3" defer></script>\n'
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    return parser.parse_args()


def inject_lookup_tracking(output: Path) -> None:
    page = output / "kiem-tra-co-phieu" / "index.html"
    if not page.is_file():
        raise RuntimeError("Lookup page missing")
    source = page.read_text(encoding="utf-8")
    if "conversion-v3.js" not in source:
        if "</head>" not in source:
            raise RuntimeError("Lookup page has no </head>")
        source = source.replace("</head>", CONVERSION_ASSETS + "</head>", 1)
    page.write_text(source, encoding="utf-8")


def patch_auth_next(output: Path) -> None:
    auth = output / "assets" / "auth.js"
    if not auth.is_file():
        raise RuntimeError("Built auth.js missing")
    source = auth.read_text(encoding="utf-8")

    old_safe_next = "const target = new URL(value, location.href);"
    new_safe_next = "const target = new URL(value, document.baseURI);"
    if old_safe_next in source:
        source, _ = _replace_once(
            source,
            old_safe_next,
            new_safe_next,
            "safeNext base resolution",
        )
    elif new_safe_next not in source:
        raise RuntimeError("safeNext base resolution is neither legacy nor completed")

    # Current auth.js owns the full plan-aware continuation contract. Do not layer
    # the old signupNext rewrite over it; doing so would erase the Premium checkout
    # destination that is persisted across OTP verification.
    completed_markers = (
        "PENDING_SIGNUP_PLAN_KEY",
        "PENDING_SIGNUP_NEXT_KEY",
        "function pendingSignupDestination()",
        "thanh-toan/?plan=premium",
    )
    if all(marker in source for marker in completed_markers):
        auth.write_text(source, encoding="utf-8")
        return

    # Backward-compatible transform for older built auth bundles. This remains so
    # the regression fixture and any stale artifact still get a safe same-origin
    # `next` flow rather than silently falling back to the account page.
    marker = "    const otpForm = document.querySelector('[data-auth-signup-otp-form]');\n    if (!form) return;"
    replacement = (
        "    const otpForm = document.querySelector('[data-auth-signup-otp-form]');\n"
        "    const signupParams = new URLSearchParams(location.search);\n"
        "    const signupNext = safeNext(signupParams.get('next'));\n"
        "    if (!form) return;"
    )
    source, _ = _replace_once(source, marker, replacement, "signup next initialization")

    source, _ = _replace_once(
        source,
        "          location.href = siteUrl('tai-khoan/?verified=1');",
        "          location.href = signupNext;",
        "OTP verified redirect",
    )

    resend = "            options: { emailRedirectTo: siteUrl('tai-khoan/?verified=1') }"
    source = source.replace(resend, "            options: { emailRedirectTo: signupNext }")
    if resend in source:
        raise RuntimeError("Signup resend redirect was not fully patched")

    signup_redirect = "          options: { emailRedirectTo: siteUrl('tai-khoan/?verified=1') }"
    source = source.replace(signup_redirect, "          options: { emailRedirectTo: signupNext }")
    if signup_redirect in source:
        raise RuntimeError("Signup email redirect was not fully patched")

    immediate = (
        "          setMessage(message, 'Tạo tài khoản thành công. Đang mở trang tài khoản…', 'success');\n"
        "          location.href = siteUrl('tai-khoan/');"
    )
    immediate_replacement = (
        "          setMessage(message, 'Tạo tài khoản thành công. Đang mở bước tiếp theo…', 'success');\n"
        "          location.href = signupNext;"
    )
    source, _ = _replace_once(source, immediate, immediate_replacement, "immediate signup redirect")

    auth.write_text(source, encoding="utf-8")


def _replace_once(source: str, old: str, new: str, label: str) -> tuple[str, int]:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"Expected exactly one {label} target, got {count}")
    return source.replace(old, new, 1), count


def main() -> None:
    output = parse_args().output.resolve()
    if not output.is_dir():
        raise RuntimeError(f"Pages output does not exist: {output}")
    inject_lookup_tracking(output)
    patch_auth_next(output)
    print("Conversion funnel v4 patch: PASS (lookup tracking + safe plan-aware Premium next-step)")


if __name__ == "__main__":
    main()
