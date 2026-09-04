#!/usr/bin/env python3
"""Apply buyer-facing truth gates after the standard Pages UX injector."""

from __future__ import annotations

import argparse
import os
import re
import shutil
from pathlib import Path


def enabled(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    return parser.parse_args()


def has_base(source: str) -> bool:
    return bool(re.search(r'<base\s+[^>]*href=["\'][^"\']+["\']', source, flags=re.IGNORECASE))


def asset_href(source: str, page: Path, output: Path, name: str) -> str:
    if has_base(source):
        return f"assets/{name}"
    target = output / "assets" / name
    return os.path.relpath(target, page.parent).replace(os.sep, "/")


def rewrite_home_lead(source: str) -> str:
    replacement = '''<article class="home-lead-card buyer-start-card">
            <span>FREE + PREMIUM</span>
            <strong>Bắt đầu với StockRadar</strong>
            <p>Tra cứu cổ phiếu, xem Radar rà soát và chọn gói phù hợp với nhu cầu phân tích.</p>
            <div class="buyer-start-actions"><a class="button button-primary" href="kiem-tra-co-phieu/">Tra cứu cổ phiếu</a><a class="button button-secondary" href="dang-ky/">Xem Free &amp; Premium</a></div>
          </article>'''
    return re.sub(
        r'<article\s+class=["\']home-lead-card["\'][^>]*>.*?</article>',
        replacement,
        source,
        count=1,
        flags=re.IGNORECASE | re.DOTALL,
    )


def rewrite_capability_copy(source: str, *, email_ready: bool, checkout_ready: bool) -> str:
    source = source.replace(
        "TOP CỔ PHIẾU KHUYẾN NGHỊ CỦA STOCKRADAR",
        "DANH SÁCH CỔ PHIẾU THEO RADAR RÀ SOÁT",
    )

    if not checkout_ready:
        source = re.sub(
            r'href=["\'](?:\.\./)*thanh-toan/\?plan=premium["\']',
            'href="dang-ky/#premium-notify-title"',
            source,
            flags=re.IGNORECASE,
        )
        source = re.sub(
            r'href=["\'](?:\.\./)*thanh-toan/["\']',
            'href="dang-ky/#premium-notify-title"',
            source,
            flags=re.IGNORECASE,
        )
        for before, after in (
            ("Thanh toán / Nâng Premium", "Đăng ký quan tâm Premium"),
            ("Nâng Premium · 199K", "Tìm hiểu Premium"),
            ("Premium · 199.000đ", "Tìm hiểu Premium"),
            ("Đăng nhập để thanh toán", "Đăng nhập"),
        ):
            source = source.replace(before, after)

    if not email_ready:
        source = rewrite_home_lead(source)
        for before, after in (
            ("StockRadar — tra cứu cổ phiếu HOSE, nhận bản rà soát 09:00 miễn phí và nâng Premium để nhận cảnh báo điểm mua/bán trong phiên.", "StockRadar — Top cổ phiếu HOSE, Radar theo ngành, phân tích đa khung và quản trị giao dịch."),
            ("StockRadar — Radar cổ phiếu HOSE & bản rà soát 09:00", "StockRadar — Top HOSE, Radar & phân tích cổ phiếu"),
            ("Tra cứu HOSE, Radar 30 cổ phiếu theo 10 ngành, nhận email Free lúc 09:00 và cảnh báo hành động Premium trong phiên.", "Tra cứu HOSE, Top cổ phiếu theo tiêu chí StockRadar, Radar 30 theo ngành và phân tích đa khung."),
            ("StockRadar — Radar HOSE & bản rà soát 09:00", "StockRadar — Top HOSE & phân tích cổ phiếu"),
            ("Nhận email 09:00", "Đăng ký"),
            ("Nhận bản tin 09:00 miễn phí", "Đăng ký Free"),
            ("FREE · EMAIL 09:00", "FREE · STOCKRADAR"),
            ("FREE 09:00 · PREMIUM TRONG PHIÊN", "TOP HOSE · RADAR · PHÂN TÍCH"),
            ("09:00 · Bản rà soát Free", "Top HOSE · StockRadar"),
            ("Free nhận bản tin 09:00.<br>Premium nhận cảnh báo trong phiên.", "Free để trải nghiệm.<br>Premium để phân tích sâu hơn."),
            ("Free: bản rà soát 09:00 · Premium: thêm cảnh báo điểm mua/bán trong phiên khi tín hiệu đủ chuẩn.", "Free: tra cứu và Radar · Premium: phân tích sâu, kế hoạch giao dịch và cảnh báo theo quyền gói."),
            ("Dành cho người muốn theo dõi thị trường và nhận bản rà soát mỗi ngày.", "Dành cho người muốn tra cứu, theo dõi Radar và đánh giá cổ phiếu HOSE."),
            ("Tra cứu, Radar, phân tích công khai và email tổng hợp để tự đánh giá cổ phiếu HOSE.", "Tra cứu, Radar và phân tích công khai để tự đánh giá cổ phiếu HOSE."),
            ("Toàn bộ quyền Free, bao gồm bản tin 09:00.", "Toàn bộ quyền Free và báo cáo phân tích chuyên sâu."),
            ("Điểm khác biệt chính: Free có bản rà soát 09:00; Premium thêm chiều sâu phân tích và cảnh báo mua/bán trong phiên.", "Điểm khác biệt chính: Free giúp tra cứu và theo dõi; Premium mở chiều sâu phân tích, kế hoạch giao dịch và cảnh báo theo quyền gói."),
            ("Ưu tiên Free email và Premium ở đúng thời điểm.", "Tra cứu, Radar và Premium theo đúng nhu cầu."),
        ):
            source = source.replace(before, after)

        source = re.sub(r"Nhận\s+email\s+09:00", "Đăng ký", source, flags=re.IGNORECASE)
        source = re.sub(
            r'<li><strong>Bản rà soát thị trường cơ bản qua email lúc 09:00 hằng ngày</strong>.*?</li>',
            '<li><strong>Top HOSE và Radar theo ngành</strong> khi dữ liệu xếp hạng đạt chuẩn.</li>',
            source,
            flags=re.IGNORECASE | re.DOTALL,
        )
        source = re.sub(
            r'<tr><td>Báo cáo email 09:00 hằng ngày</td>.*?</tr>',
            '<tr><td>Top HOSE · xếp hạng ngành</td><td class="plan-yes">Có</td><td class="plan-yes">Có · đầy đủ hơn</td></tr>',
            source,
            flags=re.IGNORECASE | re.DOTALL,
        )
    return source


def inject_assets(source: str, page: Path, output: Path, *, email_ready: bool, checkout_ready: bool) -> str:
    marker = "data-buyer-readiness-v1"
    if marker in source or "</head>" not in source:
        return source
    css = asset_href(source, page, output, "buyer-readiness-v1.css")
    js = asset_href(source, page, output, "buyer-readiness-v1.js")
    email_literal = "true" if email_ready else "false"
    checkout_literal = "true" if checkout_ready else "false"
    head = (
        f'<link rel="stylesheet" href="{css}?v=20260904-buyer1" {marker}>\n'
        '<script>window.STOCKRADAR_BUYER_CONFIG=Object.freeze({'
        f'emailDeliveryReady:{email_literal},checkoutReady:{checkout_literal}'
        '});</script>\n'
        f'<script src="{js}?v=20260904-buyer1" defer></script>\n'
    )
    return source.replace("</head>", head + "</head>", 1)


def main() -> None:
    output = parse_args().output.resolve()
    if not output.is_dir():
        raise RuntimeError(f"Pages output does not exist: {output}")

    email_ready = enabled("STOCKRADAR_PRODUCT_EMAIL_READY")
    checkout_ready = enabled("STOCKRADAR_CHECKOUT_READY")

    for required in ("buyer-readiness-v1.css", "buyer-readiness-v1.js"):
        if not (output / "assets" / required).is_file():
            raise RuntimeError(f"Missing buyer-readiness asset: {required}")

    if not checkout_ready:
        checkout = output / "thanh-toan"
        if checkout.exists():
            shutil.rmtree(checkout)

    pages = sorted(output.rglob("*.html"))
    for page in pages:
        source = page.read_text(encoding="utf-8")
        source = rewrite_capability_copy(source, email_ready=email_ready, checkout_ready=checkout_ready)
        source = inject_assets(source, page, output, email_ready=email_ready, checkout_ready=checkout_ready)
        page.write_text(source, encoding="utf-8")

    top_contract = output / "public" / "data" / "top-stocks.json"
    if not top_contract.is_file():
        raise RuntimeError("Missing public Top HOSE contract: top-stocks.json")


if __name__ == "__main__":
    main()
