#!/usr/bin/env python3
"""Force final StockRadar AI registration CTAs through the current plan page.

This runs after all Pages UX transforms. Older conversion transforms may still
rewrite AI links to the legacy /signup/ form; the published artifact must route
chat CTAs through /dang-ky/ so users first see the current Free/Premium page.
"""

from __future__ import annotations

import argparse
from pathlib import Path


REPLACEMENTS = (
    (
        "signup/?plan=premium&next=thanh-toan/%3Fplan%3Dpremium",
        "dang-ky/?plan=premium",
    ),
    ("signup/?plan=premium", "dang-ky/?plan=premium"),
    ("signup/?plan=free", "dang-ky/?plan=free"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    return parser.parse_args()


def rewrite_asset(path: Path) -> None:
    if not path.is_file():
        raise RuntimeError(f"Missing AI asset: {path}")

    source = path.read_text(encoding="utf-8")
    for old, new in REPLACEMENTS:
        source = source.replace(old, new)

    # The central AI must expose both current plan destinations. The floating
    # assistant only needs the Free registration destination when unauthenticated.
    if path.name == "ai-center.js":
        for marker in ("dang-ky/?plan=free", "dang-ky/?plan=premium"):
            if marker not in source:
                raise RuntimeError(f"Final AI center missing current registration route: {marker}")
    elif "dang-ky/?plan=free" not in source:
        raise RuntimeError("Final AI assistant missing current Free registration route")

    for stale, _ in REPLACEMENTS:
        if stale in source:
            raise RuntimeError(f"Legacy AI signup route survived final guard: {stale}")

    path.write_text(source, encoding="utf-8")


def main() -> None:
    output = parse_args().output.resolve()
    if not output.is_dir():
        raise RuntimeError(f"Pages output does not exist: {output}")

    rewrite_asset(output / "assets" / "ai-center.js")
    rewrite_asset(output / "assets" / "ai-assistant.js")
    print("AI registration CTA guard: PASS (/dang-ky/ is canonical for chat CTAs)")


if __name__ == "__main__":
    main()
