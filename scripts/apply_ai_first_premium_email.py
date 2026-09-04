#!/usr/bin/env python3
"""Apply Premium email account surfaces without rebuilding an AI-first homepage."""

from __future__ import annotations

import argparse
from pathlib import Path

import scripts.apply_premium_email_product_v1 as legacy


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    return parser.parse_args()


def main() -> None:
    output = parse_args().output.resolve()
    home = output / "index.html"
    signup = output / "signup" / "index.html"
    account = output / "tai-khoan" / "index.html"

    for path in (home, signup, account):
        if not path.is_file():
            raise RuntimeError(f"Premium email product route missing: {path}")

    home_source = home.read_text(encoding="utf-8")
    if "data-stockradar-ai-center" not in home_source:
        raise RuntimeError("AI-first Premium email adapter requires StockRadar AI homepage")
    home.write_text(legacy.inject_css(home_source), encoding="utf-8")

    signup_source = signup.read_text(encoding="utf-8")
    signup.write_text(legacy.transform_signup(signup_source), encoding="utf-8")

    account_source = account.read_text(encoding="utf-8")
    account.write_text(legacy.transform_account(account_source), encoding="utf-8")

    print("AI-first Premium email adapter: PASS (home preserved; signup/account enhanced)")


if __name__ == "__main__":
    main()
