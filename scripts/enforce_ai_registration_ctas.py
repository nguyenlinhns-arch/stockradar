#!/usr/bin/env python3
"""Force final StockRadar AI CTAs to match the Guest -> Free -> Premium funnel.

This runs after all Pages UX transforms. Older conversion transforms may still
rewrite AI links to the legacy /signup/ form. Guest registration must route to
the current /dang-ky/ Free page, while a signed-in Free account upgrades directly
through /thanh-toan/ instead of being sent through registration again.

The static builder intentionally keeps generated pages noindex by default. This
final production-only guard also makes the public homepage indexable while
leaving every other route on the conservative static-build default.
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

PUBLIC_HOME_ROBOTS = 'name="robots" content="index,follow,max-image-preview:large"'
STATIC_ROBOTS = 'name="robots" content="noindex,nofollow"'


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

    if path.name == "ai-center.js":
        # Homepage AI is account-aware: Guests can create Free; signed-in Free
        # upgrades directly to payment. Premium must never be another signup.
        for marker in ("dang-ky/?plan=free", "thanh-toan/?plan=premium", "Nâng Premium"):
            if marker not in source:
                raise RuntimeError(f"Final AI center missing current account-state CTA: {marker}")
        if "dang-ky/?plan=premium" in source:
            raise RuntimeError("Final AI center routes signed-in Premium upgrade through registration")
    elif "dang-ky/?plan=free" not in source:
        # Floating assistant may be mounted on public pages and only needs the
        # unauthenticated Free registration destination.
        raise RuntimeError("Final AI assistant missing current Free registration route")

    for stale, _ in REPLACEMENTS:
        if stale in source:
            raise RuntimeError(f"Legacy AI signup route survived final guard: {stale}")

    path.write_text(source, encoding="utf-8")


def enforce_homepage_seo(output: Path) -> None:
    page = output / "index.html"
    if not page.is_file():
        raise RuntimeError("Final homepage artifact is missing")

    source = page.read_text(encoding="utf-8")
    if PUBLIC_HOME_ROBOTS not in source:
        if STATIC_ROBOTS in source:
            source = source.replace(STATIC_ROBOTS, PUBLIC_HOME_ROBOTS, 1)
        elif "</head>" in source:
            source = source.replace("</head>", f'  <meta {PUBLIC_HOME_ROBOTS}>\n</head>', 1)
        else:
            raise RuntimeError("Final homepage has no head for public robots metadata")

    if 'rel="canonical" href="https://stockradar.vn/"' not in source:
        raise RuntimeError("Final homepage is missing canonical stockradar.vn URL")
    if STATIC_ROBOTS in source:
        raise RuntimeError("Final public homepage is still noindex")
    if PUBLIC_HOME_ROBOTS not in source:
        raise RuntimeError("Final public homepage robots metadata was not applied")

    page.write_text(source, encoding="utf-8")


def main() -> None:
    output = parse_args().output.resolve()
    if not output.is_dir():
        raise RuntimeError(f"Pages output does not exist: {output}")

    rewrite_asset(output / "assets" / "ai-center.js")
    rewrite_asset(output / "assets" / "ai-assistant.js")
    enforce_homepage_seo(output)
    print("AI account-state CTA + homepage SEO guard: PASS")


if __name__ == "__main__":
    main()
