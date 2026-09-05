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
            <p>Tra cứu cổ phiếu, xem Radar rà soát và chọn gói phù hợp với nhu cầu sử dụng.</p>
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
            ("StockRadar — tra cứu cổ phiếu HOSE, nhận bản rà soát 09:00 miễn phí và nâng Premium để nhận cảnh báo điểm mua/bán trong phiên.", "StockRadar — Top cổ phiếu HOSE, Radar theo ngành, trạng thái và quản trị rủi ro."),
            ("StockRadar — Radar cổ phiếu HOSE & bản rà soát 09:00", "StockRadar — Top HOSE, Radar & trạng thái cổ phiếu"),
            ("Tra cứu HOSE, Radar 30 cổ phiếu theo 10 ngành, nhận email Free lúc 09:00 và cảnh báo hành động Premium trong phiên.", "Tra cứu HOSE, Top cổ phiếu theo tiêu chí StockRadar, Radar 30 theo ngành và bốn khung đầu tư."),
            ("StockRadar — Radar HOSE & bản rà soát 09:00", "StockRadar — Top HOSE & trạng thái cổ phiếu"),
            ("Nhận email 09:00", "Đăng ký"),
            ("Nhận bản tin 09:00 miễn phí", "Đăng ký Free"),
            ("FREE · EMAIL 09:00", "FREE · STOCKRADAR"),
            ("FREE 09:00 · PREMIUM TRONG PHIÊN", "TOP HOSE · RADAR · QUYẾT ĐỊNH"),
            ("09:00 · Bản rà soát Free", "Top HOSE · StockRadar"),
            ("Free nhận bản tin 09:00.<br>Premium nhận cảnh báo trong phiên.", "Free để trải nghiệm.<br>Premium để biết nên làm gì."),
            ("Free: bản rà soát 09:00 · Premium: thêm cảnh báo điểm mua/bán trong phiên khi tín hiệu đủ chuẩn.", "Free: tra cứu và Radar · Premium: quyết định, kế hoạch giao dịch và cảnh báo theo quyền gói."),
            ("Dành cho người muốn theo dõi thị trường và nhận bản rà soát mỗi ngày.", "Dành cho người muốn tra cứu, theo dõi Radar và đánh giá cổ phiếu HOSE."),
            ("Tra cứu, Radar, phân tích công khai và email tổng hợp để tự đánh giá cổ phiếu HOSE.", "Tra cứu, Radar và dữ liệu công khai để tự đánh giá cổ phiếu HOSE."),
            ("Toàn bộ quyền Free, bao gồm bản tin 09:00.", "Toàn bộ quyền Free và lớp quyết định Premium."),
            ("Điểm khác biệt chính: Free có bản rà soát 09:00; Premium thêm chiều sâu phân tích và cảnh báo mua/bán trong phiên.", "Điểm khác biệt chính: Free giúp tra cứu và theo dõi; Premium mở lớp quyết định, kế hoạch giao dịch và cảnh báo theo quyền gói."),
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


def strip_analysis_jargon(source: str) -> str:
    """Keep methods internal; public Pages show only decisions, reasons and risk controls."""
    replacements = (
        ("chọn gói phù hợp với nhu cầu phân tích.", "chọn gói phù hợp với nhu cầu sử dụng."),
        ("Phương pháp quét", "Cách StockRadar rà soát"),
        ("Quét đa lớp HOSE", "Rà soát toàn thị trường HOSE"),
        ("4M · CANSLIM · Định giá · SEPA/VCP · VPA · Pocket Pivot.", "Dữ liệu thị trường, doanh nghiệp, xu hướng, dòng tiền và rủi ro được xử lý nội bộ."),
        ("Bối cảnh thị trường, ngành, doanh nghiệp, định giá, xu hướng, VPA/RVOL và dòng tiền.", "Bối cảnh thị trường, ngành, doanh nghiệp, xu hướng, dòng tiền và rủi ro."),
        ("4M · CANSLIM · Payback · Bear/Base/Bull · định giá và MOS.", "Lý do và dữ kiện hỗ trợ quyết định được StockRadar xử lý nội bộ."),
        ("SEPA/VCP · Stage · Pivot · VPA · RVOL · dòng tiền lớn.", "Theo dõi trạng thái, dòng tiền và rủi ro để cập nhật quyết định khi cần."),
        ("<strong>4M · Payback · CANSLIM</strong> cho chất lượng doanh nghiệp; <strong>Định giá Bear · Base · Bull</strong> cho biên an toàn; <strong>SEPA · VCP · Stage · VPA</strong> cho xu hướng, pivot, RVOL và dấu vết dòng tiền.", "Các dữ kiện quan trọng được tóm tắt thành lý do hỗ trợ, rủi ro và điều kiện cần theo dõi."),
        ("Pocket Pivot, Early Breakout, Confirmed Breakout, nhồi lệnh, hạ tỷ trọng hoặc cắt lỗ/bán", "trạng thái mua, giữ, tăng tỷ trọng, giảm tỷ trọng hoặc bán"),
        ("Pocket Pivot · Early Breakout · Confirmed Breakout · Retest.", "Chỉ hiển thị các mã đang ở trạng thái có thể hành động hoặc cần theo dõi."),
        ("Pocket Pivot · Early Breakout · Confirmed Breakout", "Mua · chờ · theo dõi"),
        ("Pocket Pivot · Breakout · Retest", "Mua · chờ · theo dõi · bỏ qua"),
        ("SEPA · VCP · VPA · RVOL", "TRẠNG THÁI HÀNH ĐỘNG"),
        ("setup và dữ liệu cùng đạt chuẩn", "điều kiện hành động và dữ liệu cùng đạt chuẩn"),
        ("một setup đạt chuẩn hành động", "điều kiện hành động đạt chuẩn"),
        ("Không có setup đạt chuẩn", "Không có điều kiện hành động đạt chuẩn"),
        ("setup đạt chuẩn", "điều kiện hành động đạt chuẩn"),
        ("Phân tích cơ bản · Bối cảnh để tự đánh giá", "Bối cảnh để tự đánh giá"),
        ("Phân tích cơ bản", "Bối cảnh"),
        ("Phân tích chuyên sâu", "Chi tiết quyết định"),
        ("Phân tích sâu", "Chi tiết quyết định"),
        ("Đầu ra ưu tiên quyết định trước, phương pháp và dữ liệu giải thích phía sau.", "Đầu ra ưu tiên quyết định trước; lý do và dữ kiện được tóm tắt phía sau."),
        ("<h1>Phân tích cổ phiếu</h1>", "<h1>Mã này nên làm gì?</h1>"),
        ("<title>Phân tích Free & Premium — StockRadar</title>", "<title>Tra cứu & quyết định — StockRadar</title>"),
        ("Bấm vào từng mã để mở trực tiếp trang phân tích Free/Premium.", "Bấm vào từng mã để xem trạng thái Free/Premium."),
        ("StockRadar kết hợp phân tích doanh nghiệp, định giá, kỹ thuật, dòng tiền và quản trị rủi ro.", "StockRadar tổng hợp dữ liệu thành trạng thái, vùng hành động và quản trị rủi ro."),
    )
    for before, after in replacements:
        source = source.replace(before, after)

    source = re.sub(
        r'<div class="home-tier-feature"><strong>4M · CANSLIM · Payback</strong>.*?</div>',
        '<div class="home-tier-feature"><strong>Lý do chính</strong><span>Tóm tắt các dữ kiện quan trọng hỗ trợ hoặc phản bác quyết định.</span></div>',
        source,
        flags=re.DOTALL,
    )
    source = re.sub(
        r'<div class="home-tier-feature"><strong>Định giá Bear / Base / Bull</strong>.*?</div>',
        '<div class="home-tier-feature"><strong>Biên an toàn &amp; kỳ vọng</strong><span>Cho biết dư địa tăng, rủi ro giảm và điều kiện cần theo dõi.</span></div>',
        source,
        flags=re.DOTALL,
    )
    source = re.sub(
        r'<div class="home-tier-feature"><strong>SEPA/VCP · Stage · Pivot</strong>.*?</div>',
        '<div class="home-tier-feature"><strong>Trạng thái giá</strong><span>Cho biết mã đang ở vùng chờ, vùng hành động hay đã đi quá xa.</span></div>',
        source,
        flags=re.DOTALL,
    )
    source = re.sub(
        r'<div class="home-tier-feature"><strong>VPA · RVOL · dòng tiền lớn</strong>.*?</div>',
        '<div class="home-tier-feature"><strong>Dòng tiền &amp; rủi ro</strong><span>Tóm tắt biến động đáng chú ý để hỗ trợ quyết định hiện tại.</span></div>',
        source,
        flags=re.DOTALL,
    )

    source = re.sub(
        r'<li>4M · CANSLIM · Payback · Bear/Base/Bull · định giá và MOS\.</li>',
        '<li><strong>Lý do rõ ràng:</strong> các dữ kiện quan trọng hỗ trợ hoặc phản bác quyết định.</li>',
        source,
    )
    source = re.sub(
        r'<li>SEPA/VCP · Stage · Pivot · VPA · RVOL · dòng tiền lớn\.</li>',
        '<li><strong>Theo dõi thay đổi:</strong> trạng thái được cập nhật khi dữ liệu đủ điều kiện.</li>',
        source,
    )
    source = re.sub(
        r'<tr><td>4M · CANSLIM · Payback · định giá Bear/Base/Bull</td>.*?</tr>',
        '<tr><td>Lý do và dữ kiện hỗ trợ quyết định</td><td>Tóm tắt</td><td class="plan-premium">Đầy đủ</td></tr>',
        source,
        flags=re.DOTALL,
    )

    radar_guide = '''<section class="radar-methodology" id="cach-dung-radar" aria-labelledby="radar-use-title">
      <div class="container">
        <section class="v4-fallback radar-method-card">
          <header class="v4-fallback-head radar-method-head"><div><span class="panel-label">CÁCH DÙNG RADAR</span><h2 id="radar-use-title">Nhìn trạng thái, không cần học phương pháp.</h2></div></header>
          <div class="v4-method-grid radar-method-grid">
            <article><strong>1. Chọn mã</strong><span>Xem danh sách Radar hoặc nhập mã HOSE bạn quan tâm.</span></article>
            <article><strong>2. Chọn khung</strong><span>Ngắn hạn, trung hạn, dài hạn hoặc tích sản theo nhu cầu của bạn.</span></article>
            <article><strong>3. Xem trạng thái</strong><span>Mua mới hay chờ; nếu đang nắm giữ thì giữ, tăng, giảm hay bán.</span></article>
            <article><strong>4. Quản trị rủi ro</strong><span>Xem vùng hành động, Stop, Target và điều kiện làm quyết định thay đổi.</span></article>
          </div>
          <div class="radar-vietnam-note"><strong>Nguyên tắc</strong><span>Không đủ dữ liệu hoặc điều kiện hành động → không ép đưa ra tín hiệu.</span></div>
        </section>
      </div>
    </section>'''
    source = re.sub(
        r'<section class="radar-methodology"[^>]*>.*?</section>\s*</main>',
        radar_guide + "\n  </main>",
        source,
        flags=re.DOTALL,
    )
    source = source.replace('href="#phuong-phap">Phương pháp</a>', 'href="#cach-dung-radar">Cách dùng</a>')
    source = source.replace(
        'href="#phuong-phap"><strong>Phương pháp StockRadar</strong><span>4M · CANSLIM · SEPA/VCP · VPA</span></a>',
        'href="#cach-dung-radar"><strong>Cách dùng Radar</strong><span>Mã · khung · trạng thái · rủi ro</span></a>',
    )
    source = source.replace(
        '<span>Nền tảng <strong>4M · CANSLIM · SEPA/VCP · VPA</strong></span>',
        '<span>Trạng thái <strong>MUA · CHỜ · THEO DÕI</strong></span>',
    )
    source = source.replace(
        'Radar 30 cổ phiếu HOSE theo 10 ngành, bốn khung đầu tư và bốn nền tảng 4M, CANSLIM, SEPA/VCP, VPA của StockRadar.',
        'Radar 30 cổ phiếu HOSE theo 10 ngành và bốn khung đầu tư, tập trung vào trạng thái và hành động.',
    )
    source = source.replace(
        '<meta name="description" content="Bộ lọc điểm mua StockRadar: Pocket Pivot, Early Breakout, Confirmed Breakout và Retest.">',
        '<meta name="description" content="Điểm mua StockRadar: các mã đang đạt vùng mua, chờ mua hoặc cần theo dõi.">',
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
        f'<script src="{js}?v=20260905-email1" defer></script>\n'
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


    pages = sorted(output.rglob("*.html"))
    for page in pages:
        source = page.read_text(encoding="utf-8")
        source = rewrite_capability_copy(source, email_ready=email_ready, checkout_ready=checkout_ready)
        source = strip_analysis_jargon(source)
        source = inject_assets(source, page, output, email_ready=email_ready, checkout_ready=checkout_ready)
        page.write_text(source, encoding="utf-8")

    top_contract = output / "public" / "data" / "top-stocks.json"
    if not top_contract.is_file():
        raise RuntimeError("Missing public Top HOSE contract: top-stocks.json")


if __name__ == "__main__":
    main()
