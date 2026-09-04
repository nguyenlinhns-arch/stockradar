#!/usr/bin/env python3
"""Production checks for StockRadar AI as the primary web product surface.

Supports the native AI-first homepage (`ai-center.js`, including Guest 3/day) and
the older injected inline AI center used as a backwards-compatible fallback.
"""
from __future__ import annotations

import sys
from pathlib import Path


# Keep the legacy contract explicit so older pages/builds remain verifiable.
LEGACY_HOME_COPY = (
    "Hỏi StockRadar AI trước khi ra quyết định.",
    "10 lượt hỏi mỗi ngày",
    "email Action Alert chủ động",
)


def require_markers(source: str, markers: tuple[str, ...], label: str) -> None:
    for marker in markers:
        if marker not in source:
            raise SystemExit(f"{label} missing: {marker}")


def reject_browser_secrets(source: str, label: str) -> None:
    for token in ("OPENAI_API_KEY", "SUPABASE_SERVICE_ROLE_KEY", "sb_secret_"):
        if token in source:
            raise SystemExit(f"Secret-like token must not be present in {label}: {token}")


def main() -> int:
    output = Path(sys.argv[1] if len(sys.argv) > 1 else ".pages-site").resolve()
    assistant_assets = [output / "assets" / "ai-assistant.js", output / "assets" / "ai-assistant.css"]
    for asset in assistant_assets:
        if not asset.is_file() or asset.stat().st_size < 500:
            raise SystemExit(f"Missing AI asset: {asset}")

    assistant_js = assistant_assets[0].read_text(encoding="utf-8")
    assistant_css = assistant_assets[1].read_text(encoding="utf-8")
    reject_browser_secrets(assistant_js, "AI assistant browser JS")

    require_markers(
        assistant_js,
        (
            "data-stockradar-ai-inline",
            "10 lượt mỗi ngày",
            "Tạo Free · 10 lượt/ngày",
            "PREMIUM · AI + EMAIL ACTION ALERT",
            "Free · còn",
        ),
        "AI browser product contract",
    )
    require_markers(
        assistant_css,
        (
            ".sr-ai-center",
            ".sr-ai-inline-host",
            ".sr-ai-inline-form",
            ".sr-ai-product-model",
        ),
        "AI center styling",
    )

    home = (output / "index.html").read_text(encoding="utf-8")
    native_ai_first = "assets/ai-center.js" in home and "data-stockradar-ai-center" in home

    if native_ai_first:
        center_asset = output / "assets" / "ai-center.js"
        center_css = output / "assets" / "home-ai-center-v1.css"
        for asset in (center_asset, center_css):
            if not asset.is_file() or asset.stat().st_size < 500:
                raise SystemExit(f"Missing native AI-first asset: {asset}")

        center_js = center_asset.read_text(encoding="utf-8")
        reject_browser_secrets(center_js, "native AI center browser JS")
        require_markers(
            center_js,
            (
                "stock-ai-guest",
                "stock-ai",
                "KHÁCH · 3 CÂU / NGÀY",
                "FREE · 10 CÂU / NGÀY",
                "PAID · AI KHÔNG GIỚI HẠN · EMAIL ACTION ALERT",
                "signup/?plan=free",
                "dang-ky/?plan=premium",
            ),
            "Native AI browser product contract",
        )
        require_markers(
            home,
            (
                'id="stockradar-ai"',
                "data-stockradar-ai-center",
                "3 câu/ngày",
                "10 câu/ngày",
                "Hỏi không giới hạn",
                "Action Alert",
                "Radar HOSE",
                "Khuyến nghị",
                "Hiệu quả",
                "sr-ai-nav-link",
            ),
            "Native AI-first homepage",
        )
        ai_pos = home.index('id="stockradar-ai"')
        lookup_pos = home.find("data-stock-search-form")
        radar_pos = home.find("data-live-radar-home")
        if lookup_pos < 0 or radar_pos < 0 or not (ai_pos < lookup_pos < radar_pos):
            raise SystemExit("Native StockRadar AI center must appear before lookup and supporting Radar")
    else:
        require_markers(
            home,
            (
                'id="stockradar-ai"',
                "data-stockradar-ai-center",
                "data-stockradar-ai-inline",
                *LEGACY_HOME_COPY,
                "FREE",
                "PREMIUM",
                "Radar HOSE",
                "Khuyến nghị",
                "Hiệu quả",
                "sr-ai-nav-link",
            ),
            "Legacy AI-first homepage",
        )
        if "SAU KHI TRA MÃ" in home and home.index('id="stockradar-ai"') > home.index("SAU KHI TRA MÃ"):
            raise SystemExit("StockRadar AI center must appear before legacy/product supporting sections")

    if home.count("<h1") != 1:
        raise SystemExit("StockRadar AI center must own the single homepage H1")

    # The supporting AI assistant must remain available on core product pages,
    # even when the homepage uses the newer guest-capable native AI center.
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

    print("StockRadar AI production surface verified: AI-first + Guest 3/day + Free 10/day + Paid unlimited/email entitlement")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
