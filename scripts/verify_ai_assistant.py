#!/usr/bin/env python3
"""Production checks for the StockRadar AI web assistant."""
from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    output = Path(sys.argv[1] if len(sys.argv) > 1 else ".pages-site").resolve()
    required_assets = [output / "assets" / "ai-assistant.js", output / "assets" / "ai-assistant.css"]
    for asset in required_assets:
        if not asset.is_file() or asset.stat().st_size < 200:
            raise SystemExit(f"Missing AI asset: {asset}")
    js = required_assets[0].read_text(encoding="utf-8")
    forbidden = ("OPENAI_API_KEY", "SUPABASE_SERVICE_ROLE_KEY", "sb_secret_")
    for token in forbidden:
        if token in js:
            raise SystemExit(f"Secret-like token must not be present in browser JS: {token}")
    for relative in ("index.html", "kiem-tra-co-phieu/index.html", "radar5/index.html", "khuyen-nghi/index.html"):
        source = (output / relative).read_text(encoding="utf-8")
        if "assets/ai-assistant.js" not in source or "assets/ai-assistant.css" not in source:
            raise SystemExit(f"AI assistant missing from: {relative}")
    print("StockRadar AI production surface verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
