#!/usr/bin/env python3
"""Production checks for StockRadar AI as the primary web product surface."""
from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    output = Path(sys.argv[1] if len(sys.argv) > 1 else ".pages-site").resolve()
    required_assets = [output / "assets" / "ai-assistant.js", output / "assets" / "ai-assistant.css"]
    for asset in required_assets:
        if not asset.is_file() or asset.stat().st_size < 500:
            raise SystemExit(f"Missing AI asset: {asset}")

    js = required_assets[0].read_text(encoding="utf-8")
    css = required_assets[1].read_text(encoding="utf-8")
    forbidden = ("OPENAI_API_KEY", "SUPABASE_SERVICE_ROLE_KEY", "sb_secret_")
    for token in forbidden:
        if token in js:
            raise SystemExit(f"Secret-like token must not be present in browser JS: {token}")

    for marker in (
        "data-stockradar-ai-inline",
        "10 lượt mỗi ngày",
        "Tạo Free · 10 lượt/ngày",
        "PREMIUM · AI + EMAIL ACTION ALERT",
        "Free · còn",
    ):
        if marker not in js:
            raise SystemExit(f"AI browser product contract missing: {marker}")

    for marker in (
        ".sr-ai-center",
        ".sr-ai-inline-host",
        ".sr-ai-inline-form",
        ".sr-ai-product-model",
    ):
        if marker not in css:
            raise SystemExit(f"AI center styling missing: {marker}")

    home = (output / "index.html").read_text(encoding="utf-8")
    required_home = (
        'id="stockradar-ai"',
        "data-stockradar-ai-center",
        "data-stockradar-ai-inline",
        "Hỏi StockRadar AI trước khi ra quyết định.",
        "FREE",
        "10 lượt hỏi mỗi ngày",
        "PREMIUM",
        "email Action Alert chủ động",
        "Radar HOSE",
        "Khuyến nghị",
        "Hiệu quả",
        "sr-ai-nav-link",
    )
    for marker in required_home:
        if marker not in home:
            raise SystemExit(f"Homepage is not AI-first; missing: {marker}")
    if home.index('id="stockradar-ai"') > home.index("SAU KHI TRA MÃ"):
        raise SystemExit("StockRadar AI center must appear before legacy/product supporting sections")
    if home.count("<h1") != 1:
        raise SystemExit("StockRadar AI center must own the single homepage H1")

    for relative in (
        "index.html",
        "hom-nay/index.html",
        "kiem-tra-co-phieu/index.html",
        "radar5/index.html",
        "khuyen-nghi/index.html",
        "hieu-qua/index.html",
    ):
        source = (output / relative).read_text(encoding="utf-8")
        if "assets/ai-assistant.js" not in source or "assets/ai-assistant.css" not in source:
            raise SystemExit(f"AI assistant missing from: {relative}")
        if "sr-ai-nav-link" not in source:
            raise SystemExit(f"AI navigation missing from: {relative}")

    print("StockRadar AI production surface verified: AI-first homepage + Free 10/day + Premium proactive email positioning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
