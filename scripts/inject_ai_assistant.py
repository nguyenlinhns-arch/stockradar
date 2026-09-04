#!/usr/bin/env python3
"""Inject the StockRadar AI assistant into production-facing Pages HTML."""
from __future__ import annotations

import sys
from pathlib import Path

HEAD = '''<link rel="stylesheet" href="assets/ai-assistant.css?v=20260904-ai1">\n<script src="assets/ai-assistant.js?v=20260904-ai1" defer></script>\n'''
SKIP_TOP_ROUTES = {"signup", "dang-ky", "dang-nhap", "dat-lai-mat-khau", "tai-khoan", "dieu-khoan", "quyen-rieng-tu", "email"}


def should_inject(relative: Path) -> bool:
    if relative.name == "404.html":
        return False
    return not (relative.parts and relative.parts[0] in SKIP_TOP_ROUTES)


def main() -> int:
    output = Path(sys.argv[1] if len(sys.argv) > 1 else ".pages-site").resolve()
    if not output.is_dir():
        raise SystemExit(f"Pages output not found: {output}")
    for asset in (output / "assets" / "ai-assistant.js", output / "assets" / "ai-assistant.css"):
        if not asset.is_file() or asset.stat().st_size < 200:
            raise SystemExit(f"Missing StockRadar AI asset: {asset}")

    injected = 0
    for page in output.rglob("*.html"):
        relative = page.relative_to(output)
        if not should_inject(relative):
            continue
        source = page.read_text(encoding="utf-8")
        if "assets/ai-assistant.js" in source:
            continue
        if "</head>" not in source:
            raise SystemExit(f"HTML page has no closing head tag: {relative}")
        page.write_text(source.replace("</head>", HEAD + "</head>", 1), encoding="utf-8")
        injected += 1
    if injected < 5:
        raise SystemExit(f"AI assistant injected into too few pages: {injected}")
    print(f"StockRadar AI assistant injected into {injected} pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
