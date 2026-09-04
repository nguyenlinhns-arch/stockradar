#!/usr/bin/env python3
"""Patch the built Pages artifact for a continuous Premium buyer journey.

Goals:
- direct /kiem-tra-co-phieu/ visits use the same privacy-minimal conversion tracker;
- safe `next` URLs resolve from the site base, not from /signup/;
- Premium signup/OTP returns to the requested same-origin next step when provided;
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

    source, count = _replace_once(
        source,
        "const target = new URL(value, location.href);",
        "const target = new URL(value, document.baseURI);",
        "safeNext base resolution",
    )

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
    print("Conversion funnel v4 patch: PASS (lookup tracking + Premium next-step)")


if __name__ == "__main__":
    main()
