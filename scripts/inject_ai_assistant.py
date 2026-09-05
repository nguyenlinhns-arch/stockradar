#!/usr/bin/env python3
"""Make StockRadar AI the primary production-facing StockRadar experience.

This transform runs after the other homepage/product transforms so a later legacy
layout pass cannot push AI back into a secondary floating-only role.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path


HEAD = '''<link rel="stylesheet" href="assets/ai-assistant.css?v=20260904-ai2">\n<script src="assets/auth-state-v2.js?v=20260905-authstate3" defer></script>\n<script src="assets/ai-assistant.js?v=20260905-decision1" defer></script>\n'''
DECISION_HEAD = '''<link rel="stylesheet" href="assets/ai-decision-view.css?v=20260905-decision1">\n<script src="assets/ai-decision-view.js?v=20260905-decision1" defer></script>\n'''
SKIP_TOP_ROUTES = {
    "signup",
    "dang-ky",
    "dang-nhap",
    "dat-lai-mat-khau",
    "thanh-toan",
    "dieu-khoan",
    "quyen-rieng-tu",
    "email",
    "nhan-ban-tin",
    "huy-dang-ky-email",
}

HOME_CENTER = '''<section class="sr-ai-center" id="stockradar-ai" data-stockradar-ai-center aria-labelledby="stockradar-ai-title">
      <div class="sr-ai-center-inner">
        <div class="sr-ai-center-head">
          <div>
            <span class="sr-ai-kicker">✦ TRUNG TÂM STOCKRADAR</span>
            <h1 id="stockradar-ai-title">Hỏi StockRadar AI trước khi ra quyết định.</h1>
            <p class="sr-ai-center-intro"><strong>Nhập một mã HOSE hoặc hỏi về danh mục của bạn.</strong> StockRadar AI đọc dữ liệu, trạng thái và các lớp phân tích phía sau để trả lời trực tiếp: mua mới hay chờ, đang nắm giữ nên làm gì, rủi ro ở đâu và điều kiện nào làm thay đổi quyết định.</p>
          </div>
          <div class="sr-ai-product-model" aria-label="Mô hình Free và Premium">
            <div><b>FREE</b><span>Cùng lõi phân tích AI · <strong>10 lượt hỏi mỗi ngày</strong> · tự vào hỏi khi cần.</span></div>
            <div class="is-premium"><b>PREMIUM</b><span>StockRadar AI + <strong>email Action Alert chủ động</strong> ngay sau khi hệ thống xác nhận trạng thái hành động mới trong phiên.</span></div>
          </div>
        </div>

        <div class="sr-ai-console-shell">
          <div class="sr-ai-inline-host" data-stockradar-ai-inline aria-label="Hỏi StockRadar AI"></div>
          <aside class="sr-ai-evidence" aria-label="Nguồn bằng chứng phía sau StockRadar AI">
            <p class="sr-ai-evidence-title">DỮ LIỆU &amp; BẰNG CHỨNG PHÍA SAU AI</p>
            <a href="radar5/"><strong>Radar HOSE</strong><span>Quét và xếp hạng cơ hội đủ điều kiện theo snapshot.</span></a>
            <a href="khuyen-nghi/"><strong>Khuyến nghị</strong><span>Trạng thái hành động, vùng mua, Stop, Target và lịch sử thay đổi.</span></a>
            <a href="hieu-qua/"><strong>Hiệu quả</strong><span>Kiểm chứng khuyến nghị có dấu thời gian thay vì chỉ tin câu trả lời.</span></a>
          </aside>
        </div>

        <div class="sr-ai-center-foot">
          <span><strong>Free:</strong> 10 lượt/ngày, reset 00:00 giờ Việt Nam.</span>
          <span><strong>Premium:</strong> không cần tự canh; Action Alert được tạo khi quyết định đủ điều kiện thay đổi.</span>
          <span>Không đủ Data Gate → AI nói chưa đủ dữ liệu, không tự bịa giá hoặc tín hiệu.</span>
        </div>
      </div>
    </section>'''


def should_inject(relative: Path) -> bool:
    if relative.name == "404.html":
        return False
    return not (relative.parts and relative.parts[0] in SKIP_TOP_ROUTES)


def inject_nav(source: str) -> str:
    if "sr-ai-nav-link" in source:
        return source
    pattern = r'(<nav class="nav-links"[^>]*>)'
    replacement = r'\1<a class="sr-ai-nav-link" href="./#stockradar-ai">StockRadar AI</a>'
    return re.sub(pattern, replacement, source, count=1)


def transform_home(source: str) -> str:
    if 'data-stockradar-ai-center' in source:
        # Native AI-first homepage: preserve its layout/client and only guarantee
        # the shared navigation anchor used by StockRadar AI links on every page.
        if 'id="stockradar-ai"' not in source:
            source = source.replace(
                'data-stockradar-ai-center',
                'id="stockradar-ai" data-stockradar-ai-center',
                1,
            )
        return source

    # Legacy homepage fallback: inject the original inline AI center and make it
    # own the single H1.
    source = re.sub(
        r'<h1>(.*?)</h1>',
        r'<h2 class="sr-ai-support-title">\1</h2>',
        source,
        count=1,
        flags=re.DOTALL,
    )

    main_match = re.search(r'<main\b[^>]*>', source)
    if not main_match:
        raise RuntimeError("Homepage has no <main> element for StockRadar AI center")
    insert_at = main_match.end()
    source = source[:insert_at] + "\n    " + HOME_CENTER + source[insert_at:]
    return source


def main() -> int:
    output = Path(sys.argv[1] if len(sys.argv) > 1 else ".pages-site").resolve()
    if not output.is_dir():
        raise SystemExit(f"Pages output not found: {output}")
    for asset in (
        output / "assets" / "auth-state-v2.js",
        output / "assets" / "ai-assistant.js",
        output / "assets" / "ai-assistant.css",
    ):
        if not asset.is_file() or asset.stat().st_size < 500:
            raise SystemExit(f"Missing StockRadar AI asset: {asset}")

    injected = 0
    for page in output.rglob("*.html"):
        relative = page.relative_to(output)
        if not should_inject(relative):
            continue
        source = page.read_text(encoding="utf-8")
        if "assets/ai-decision-view.js" not in source:
            source = source.replace("</head>", DECISION_HEAD + "</head>", 1)
        source = inject_nav(source)
        if relative == Path("index.html"):
            source = transform_home(source)
        if "assets/ai-assistant.js" not in source:
            if "</head>" not in source:
                raise SystemExit(f"HTML page has no closing head tag: {relative}")
            source = source.replace("</head>", HEAD + "</head>", 1)
        page.write_text(source, encoding="utf-8")
        injected += 1

    if injected < 8:
        raise SystemExit(f"AI assistant injected into too few pages: {injected}")
    print(f"StockRadar AI centered on homepage and injected into {injected} pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
