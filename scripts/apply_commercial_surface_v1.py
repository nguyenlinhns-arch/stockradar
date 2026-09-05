#!/usr/bin/env python3
"""Apply the final commercial StockRadar surface to the built Pages artifact."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

STYLE_NAME = "commercial-v1.css"
STYLE_MARKER = "data-commercial-v1"
COMMERCIAL_SCRIPT_NAME = "commercial-v1.js"
COMMERCIAL_RUNTIME_MARKER = "data-commercial-runtime-v1"
NOTIFICATION_STYLE_NAME = "header-notifications.css"
NOTIFICATION_SCRIPT_NAME = "header-notifications.js"
NOTIFICATION_MARKER = "data-header-notifications-v1"
SUPABASE_BROWSER_SRC = "https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"
CORE_ROUTES = ("", "hom-nay", "radar5", "kiem-tra-co-phieu", "khuyen-nghi", "nganh", "hieu-qua", "dang-ky", "tai-khoan")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    return parser.parse_args()


def read(path: Path) -> str:
    if not path.is_file():
        raise RuntimeError(f"Commercial surface target missing: {path}")
    return path.read_text(encoding="utf-8")


def write(path: Path, source: str) -> None:
    path.write_text(source, encoding="utf-8")


def inject_style(source: str) -> str:
    if "</head>" not in source:
        raise RuntimeError("Commercial surface page has no closing head tag")
    tags: list[str] = []
    if STYLE_MARKER not in source:
        tags.append(f'<link rel="stylesheet" href="assets/{STYLE_NAME}?v=20260904-commercial2" {STYLE_MARKER}>')
    if COMMERCIAL_RUNTIME_MARKER not in source:
        tags.append(f'<script src="assets/{COMMERCIAL_SCRIPT_NAME}?v=20260904-commercial2" defer {COMMERCIAL_RUNTIME_MARKER}></script>')
    if not tags:
        return source
    return source.replace("</head>", "\n".join(tags) + "\n</head>", 1)


def inject_notification_assets(source: str) -> str:
    """Add the owner-only notification bell only to auth-aware pages with the shared site header."""
    if NOTIFICATION_MARKER in source:
        return source
    if "assets/auth-config.js" not in source or "site-header" not in source:
        return source
    if "</head>" not in source:
        raise RuntimeError("Notification target page has no closing head tag")

    tags = [
        f'<link rel="stylesheet" href="assets/{NOTIFICATION_STYLE_NAME}?v=20260904-alert1" {NOTIFICATION_MARKER}>',
    ]
    if SUPABASE_BROWSER_SRC not in source:
        tags.append(f'<script src="{SUPABASE_BROWSER_SRC}" defer></script>')
    tags.append(f'<script src="assets/{NOTIFICATION_SCRIPT_NAME}?v=20260904-alert1" defer></script>')
    return source.replace("</head>", "\n".join(tags) + "\n</head>", 1)


def inject_notification_assets_all(output: Path) -> int:
    changed = 0
    for page in output.rglob("*.html"):
        source = read(page)
        patched = inject_notification_assets(source)
        if patched != source:
            write(page, patched)
            changed += 1
    if changed < 1:
        raise RuntimeError("Notification bell injection found no auth-aware Pages")
    return changed


def remove_section(source: str, class_name: str, *, required: bool = True) -> str:
    pattern = re.compile(rf'\s*<section\b[^>]*class=["\'][^"\']*\b{re.escape(class_name)}\b[^"\']*["\'][^>]*>.*?</section>\s*', re.I | re.S)
    source, count = pattern.subn("\n", source, count=1)
    if required and count != 1:
        raise RuntimeError(f"Commercial surface expected section .{class_name}, found {count}")
    return source


def remove_section_by_aria(source: str, aria_id: str) -> str:
    return re.sub(rf'\s*<section\b[^>]*aria-labelledby=["\']{re.escape(aria_id)}["\'][^>]*>.*?</section>\s*', "\n", source, count=1, flags=re.I | re.S)


def remove_conversion_rail(source: str) -> str:
    return remove_section(source, "conversion-rail", required=False)


def normalize_nav(source: str, current: str = "") -> str:
    def link(href: str, label: str, route: str = "") -> str:
        current_attr = ' aria-current="page"' if current == route and route else ""
        return f'<a href="{href}"{current_attr}>{label}</a>'
    nav = '<nav class="nav-links" id="site-menu" aria-label="Điều hướng chính" data-nav-menu>' + link("./#stockradar-ai", "AI") + link("hom-nay/", "Hôm nay", "hom-nay") + link("radar5/", "Radar", "radar5") + link("khuyen-nghi/", "Khuyến nghị", "khuyen-nghi") + link("hieu-qua/", "Hiệu quả", "hieu-qua") + "</nav>"
    source, count = re.subn(r'<nav\b[^>]*data-nav-menu[^>]*>.*?</nav>', nav, source, count=1, flags=re.I | re.S)
    if count != 1:
        raise RuntimeError("Commercial surface could not normalize primary navigation")
    return source


def normalize_footer(source: str) -> str:
    footer = '<footer class="site-footer commercial-footer"><div class="container"><div class="footer-grid"><strong>STOCKRADAR.VN</strong><div class="footer-links"><a href="dieu-khoan/">Điều khoản</a><a href="quyen-rieng-tu/">Quyền riêng tư</a></div></div><p class="disclaimer">Công cụ hỗ trợ quyết định đầu tư. Không cam kết lợi nhuận, không tự đặt lệnh.</p></div></footer>'
    source, count = re.subn(r'<footer\b[^>]*class=["\'][^"\']*\bsite-footer\b[^"\']*["\'][^>]*>.*?</footer>', footer, source, count=1, flags=re.I | re.S)
    if count != 1:
        raise RuntimeError("Commercial surface could not normalize footer")
    return source


def normalize_header_register(source: str) -> str:
    source = re.sub(r'(<a\b[^>]*class=["\'][^"\']*\bheader-register-cta\b[^"\']*["\'][^>]*href=["\'])[^"\']+(["\'])', r'\1dang-ky/?plan=free\2', source, flags=re.I)
    return source.replace(">Đăng ký miễn phí</a>", ">Bắt đầu miễn phí</a>")


def commercial_home(source: str) -> str:
    source = remove_section(source, "buyer-first-section")
    proof = '<section class="home-section commercial-proof" aria-label="Kiểm chứng StockRadar"><div class="container commercial-proof-bar"><div><span>Đã báo mua</span><strong data-proof-total>—</strong></div><div><span>Chưa có email bán</span><strong data-proof-open>—</strong></div><div><span>Mã đã báo bán</span><strong data-proof-closed>—</strong></div><div><span>Lãi/lỗ đã chốt</span><strong data-proof-return>—</strong></div><a href="hieu-qua/">Hiệu quả →</a><a href="radar5/">Radar →</a></div></section>'
    source, count = re.subn(r'\s*<section class="home-section" aria-labelledby="proof-title">.*?</section>\s*', proof, source, count=1, flags=re.I | re.S)
    if count != 1:
        raise RuntimeError("Commercial homepage proof section not found")
    source = re.sub(r'\s*<form class="email-mini home-email-form".*?</form>\s*', "\n", source, count=1, flags=re.I | re.S)
    replacements = (
        ("Hỏi thẳng điều bạn cần biết: mua mới hay chờ, đang nắm giữ nên làm gì, vùng giá nào đáng chú ý và rủi ro nào có thể làm thay đổi quyết định.", "Mua hay chờ · Giữ hay bán · Vùng giá · Rủi ro."),
        ("Dữ liệu hành động mới nhất đã được StockRadar cho phép phát hành.", "Tín hiệu mới nhất."),
        ("Chỉ hiển thị khi dữ liệu đạt điều kiện phát hành. Không có mã đạt chuẩn cũng là một kết quả hợp lệ.", "Chỉ hiển thị tín hiệu đủ chuẩn."),
        ("Dùng AI trước. Nâng cấp khi cần nhiều hơn và cần theo dõi chủ động.", "Chọn mức sử dụng."),
        ("Khách có 3 câu/ngày. Free có 10 câu/ngày. Premium hỏi không giới hạn và có quyền nhận Action Alert khi hệ thống email production được kích hoạt.", "Free để tự tra cứu. Premium để nhận cảnh báo tự động."),
        ("Dành cho người muốn tự hỏi AI, tra cứu mã và lưu danh sách theo dõi cơ bản.", "AI + tra cứu + watchlist cơ bản."),
        ("AI không giới hạn, lớp quyết định đầy đủ và quyền nhận Daily 09:00 / cảnh báo trong phiên sau khi email production đủ điều kiện vận hành.", "Báo thay đổi mã theo dõi, kèm mức giá và giờ xác nhận sau mỗi lượt quét trong phiên."),
    )
    for before, after in replacements:
        source = source.replace(before, after)
    return source


def commercial_today(source: str) -> str:
    source = remove_section_by_aria(source, "paid-shortcuts-title")
    return source.replace("Việc cần làm trước · mã đang sở hữu · mã theo dõi · thay đổi mới · trạng thái cảnh báo.", "Hành động · vị thế · watchlist · thay đổi mới.")


def commercial_radar(source: str) -> str:
    source = remove_section(source, "radar-methodology")
    source = remove_section(source, "operations-shortcuts", required=False)
    source = remove_conversion_rail(source)
    replacements = (
        ("Radar toàn bộ cổ phiếu HOSE", "Radar HOSE"),
        ("Quét full-universe → kiểm tra dữ liệu/thanh khoản → chấm điểm đa lớp → xếp hạng → Action Gate. Không đủ chuẩn thì không đưa vào danh sách hành động.", "Toàn HOSE. Chỉ hiển thị mã đủ điều kiện."),
        ("FULL HOSE · GATED RADAR", "TOÀN HOSE"),
        ("NGẮN HẠN · 5–20 PHIÊN", "RADAR HOSE"),
        ("Radar theo trạng thái hành động", "Cơ hội theo trạng thái"),
        ("Dữ liệu · thanh khoản · bối cảnh · rủi ro", "Đủ điều kiện"),
        ("khối lượng tương đối và volume được so cùng tiến độ phiên, không dùng volume cả ngày máy móc.", "4 mốc rà soát trong phiên."),
    )
    for before, after in replacements:
        source = source.replace(before, after)
    return re.sub(r'<a\b[^>]*href=["\']#(?:cach-dung-radar|phuong-phap)["\'][^>]*>.*?</a>', "", source, flags=re.I | re.S)


def commercial_lookup(source: str) -> str:
    source = remove_conversion_rail(source)
    source = source.replace("Nhập mã để xem dữ liệu thị trường tham chiếu ngay và trạng thái StockRadar theo bốn khung đầu tư khi Decision Feed đạt gate.", "Nhập mã HOSE để xem trạng thái StockRadar.")
    return source.replace("TOÀN HOSE · 4 KHUNG ĐẦU TƯ", "TRA CỨU HOSE")


def commercial_recommendations(source: str) -> str:
    source = remove_section(source, "buyer-recommendation-contract")
    source = remove_conversion_rail(source)
    source = re.sub(r'<div class="home-recommendation-status">.*?</div>\s*<section class="recommendation-reference-list"', '<div class="commercial-reco-summary"><div><span>Tín hiệu hiện tại</span><strong data-current-action-count>0 mã</strong></div><div><span>Phạm vi</span><strong>Toàn HOSE</strong></div></div><section class="recommendation-reference-list"', source, count=1, flags=re.I | re.S)
    source = re.sub(r'\s*<p class="recommendation-reference-note">.*?</p>\s*', "\n", source, count=1, flags=re.I | re.S)
    replacements = (
        ("StockRadar quét toàn HOSE nhưng không ép đủ số lượng. Chỉ mã vượt qua dữ liệu, thanh khoản, bối cảnh, chất lượng điểm vào và quản trị rủi ro mới được chuyển từ Radar sang tín hiệu hành động.", "Tín hiệu hành động đã được StockRadar phát hành."),
        ("FULL HOSE · ACTION GATED", "TÍN HIỆU ĐÃ PHÁT HÀNH"),
        ("RADAR → ACTION GATE", "RADAR"),
        ("Shortlist theo snapshot", "Danh sách theo dõi"),
    )
    for before, after in replacements:
        source = source.replace(before, after)
    source = source.replace('</main>', '<section class="container"><div data-alert-history><p>Đang tải lịch sử email…</p></div></section></main>', 1)
    source = source.replace('</head>', '<link rel="stylesheet" href="assets/recommendation-history.css?v=1"><script src="assets/recommendation-history.js?v=1" defer></script></head>', 1)
    source = source.replace('Tín hiệu hiện tại</span>', 'Điểm mua mới</span>')
    return source


def commercial_sectors(source: str) -> str:
    source = remove_conversion_rail(source)
    source = source.replace("10 nhóm ngành · 3 mã mỗi ngành · 30 cổ phiếu HOSE.", "So sánh sức mạnh cổ phiếu theo ngành trên HOSE.")
    return source.replace("SO SÁNH CÙNG NGÀNH", "THEO NGÀNH")


def commercial_performance(source: str) -> str:
    source = remove_section(source, "buyer-first-section")
    source = remove_conversion_rail(source)
    source = source.replace("Kích hoạt · Entry · Target/Stop · Benchmark. Người mua phải kiểm chứng được cả kết quả tốt lẫn kết quả xấu.", "Lịch sử email và biến động giá từng mã.")
    source = source.replace("KẾT QUẢ · CÓ DẤU THỜI GIAN", "KẾT QUẢ THỰC TẾ")
    audit = '<div class="container commercial-audit-strip"><span>Email đã đối chiếu</span><span>Giờ gửi thực tế</span><span>Biến động giá</span><span>Rà soát tháng 8</span></div>'
    return source.replace('<section class="performance-workspace">', '<section class="performance-workspace">' + audit, 1)


def commercial_plans(source: str) -> str:
    # These are legacy compatibility anchors. Upstream reducers may already have
    # removed them, so the final pass must remain idempotent.
    source = remove_section(source, "conversion-plan-value", required=False)
    source = remove_section(source, "buyer-plan-value", required=False)
    source = re.sub(r'\s*<section class="plan-comparison" aria-labelledby="premium-notify-title">.*?</section>\s*', "\n", source, count=1, flags=re.I | re.S)

    free_card = '''<article class="plan-card commercial-plan-card" data-plan-free>
            <span class="plan-kicker">FREE</span><h2>StockRadar Free</h2>
            <div class="plan-price"><strong>0đ</strong></div>
            <p class="plan-summary">Dùng StockRadar AI và các công cụ cơ bản.</p>
            <ul class="plan-feature-list"><li>AI 10 câu/ngày</li><li>Tra cứu cổ phiếu HOSE</li><li>Radar &amp; hiệu quả</li><li>Watchlist cơ bản</li></ul>
            <div class="plan-info-box">Không có email điểm mua/bán.</div>
            <a class="button button-secondary" href="signup/?plan=free" data-registration-plan="free">Đăng ký Free</a>
          </article>'''
    source, free_count = re.subn(r'<article\b[^>]*data-plan-free[^>]*>.*?</article>', free_card, source, count=1, flags=re.I | re.S)
    if free_count != 1:
        raise RuntimeError("Commercial Free plan card not found")

    premium_card = '''<article class="plan-card plan-card-premium conversion-plan-card commercial-plan-card" data-plan-premium id="premium" data-checkout-ready="true">
            <span class="plan-ribbon">EMAIL TỰ ĐỘNG</span><span class="plan-kicker">PREMIUM</span><h2>StockRadar Premium</h2>
            <div class="plan-price"><strong>199.000đ</strong><span>/ 30 ngày</span></div>
            <p class="plan-summary">Email cập nhật điểm mua/bán của mã theo dõi.</p>
            <ul class="plan-feature-list"><li>Báo khi đổi trạng thái mua / giữ / giảm / bán</li><li>Kèm mức giá, lý do và giờ xác nhận</li><li>Bản tin 09:00 và cảnh báo trong phiên*</li><li>AI không giới hạn để hỏi sâu</li></ul>
            <div class="plan-info-box plan-info-box-premium">Chọn mã → bật nhận email → nhận thay đổi đã xác nhận.</div>
            <a class="button button-primary" href="signup/?plan=premium&amp;next=thanh-toan/%3Fplan%3Dpremium" data-registration-plan="premium" data-premium-conversion-cta data-conversion-action="plans_premium">Đăng ký Premium</a>
          </article>'''
    source, premium_count = re.subn(r'<article\b[^>]*data-plan-premium[^>]*>.*?</article>', premium_card, source, count=1, flags=re.I | re.S)
    if premium_count != 1:
        raise RuntimeError("Commercial Premium plan card not found")

    comparison = '''<section class="plan-comparison commercial-plan-comparison" data-plan-comparison aria-labelledby="compare-title"><div class="plan-comparison-header"><span class="plan-kicker">SO SÁNH</span><h2 id="compare-title">Free và Premium</h2></div><div class="plan-table-wrap"><table class="plan-table"><thead><tr><th>Tính năng</th><th>Free</th><th>Premium</th></tr></thead><tbody><tr><td>Email điểm mua/bán tự động</td><td>Không</td><td>Có*</td></tr><tr><td>Bản tin 09:00</td><td>Không</td><td>Có*</td></tr><tr><td>Vùng mua / cắt lỗ / mục tiêu</td><td>Không</td><td>Khi được xác nhận</td></tr><tr><td>StockRadar AI</td><td>10 câu/ngày</td><td>Không giới hạn</td></tr><tr><td>Tra cứu / Radar</td><td>Có</td><td>Có</td></tr></tbody></table></div><p class="plan-price-note">* Email chưa bật. Xem lịch và trạng thái gửi trên trang chủ.</p></section>'''
    source, comparison_count = re.subn(r'<section class="plan-comparison"\s+data-plan-comparison.*?</section>', comparison, source, count=1, flags=re.I | re.S)
    if comparison_count != 1:
        raise RuntimeError("Commercial plan comparison not found")

    source = source.replace("Chọn Free hoặc đăng ký Premium", "Email tự động báo điểm mua/bán")
    source = source.replace("Chọn gói StockRadar", "Email tự động báo điểm mua/bán")
    source = re.sub(r'<p>Premium: tạo tài khoản → thanh toán 199\.000đ/30 ngày\. Không cần tạo Free rồi mới nâng cấp\.</p>', "", source, count=1)
    source = re.sub(r'<script[^>]+src=["\'][^"\']*assets/email-interest\.js[^"\']*["\'][^>]*></script>\s*', "", source, flags=re.I)
    return source


def commercial_account(source: str) -> str:
    source = remove_section(source, "my-stockradar-hero", required=False)
    replacements = (
        ("Quản lý watchlist, mã đang sở hữu, email Premium, cảnh báo và bảo mật.", "Watchlist · vị thế · cảnh báo · bảo mật."),
        ("Chỉ hiển thị thay đổi trạng thái hành động đã qua đầy đủ gate dữ liệu và đúng mã/khung bạn bật cảnh báo.", ""),
        ("StockRadar có đang canh email cho bạn không?", "Email Premium"),
        ("Kiểm tra nhanh cấu hình theo dõi và lần giao email gần nhất của chính tài khoản này.", "Trạng thái email Premium của tài khoản."),
        ("Chọn chính xác loại thông tin bạn muốn StockRadar chủ động gửi. Không có email mua/bán nếu không có tín hiệu hành động đủ điều kiện.", "Chọn loại email Premium bạn muốn nhận."),
        ("Bản chủ động theo watchlist và việc cần chú ý, chỉ dành cho Trial/Paid khi delivery production đạt chuẩn.", "Daily 09:00 theo watchlist."),
        ("Gửi khi có hành động được xác nhận: đạt điểm mua, nhồi lệnh, hạ tỷ trọng, cắt lỗ/bán hoặc thay đổi trạng thái quan trọng.", "Gửi khi trạng thái hành động thay đổi."),
        ("Cần tài khoản Trial/Paid, email đã xác minh và hệ thống delivery production đã được kích hoạt.", "Trial/Premium · email production sẵn sàng."),
        ("Bạn có thể đổi lựa chọn hoặc rút đăng ký email bất kỳ lúc nào.", "Có thể thay đổi bất kỳ lúc nào."),
        ("StockRadar không yêu cầu tài khoản chứng khoán, OTP, số lượng cổ phiếu, NAV hay quyền giao dịch. Nếu muốn AI cá nhân hóa sâu hơn, bạn có thể tự nguyện nhập giá vốn và tỷ trọng ước tính cho mã đang sở hữu.", "Có thể nhập giá vốn và tỷ trọng ước tính nếu muốn cá nhân hóa sâu hơn."),
        ("Tôi đang sở hữu mã này — dùng để tách riêng quyết định “đang nắm giữ” khỏi “mua mới”.", "Tôi đang sở hữu mã này"),
        ("Dữ liệu tự khai báo:", "Tùy chọn:"),
        ("giá vốn/tỷ trọng chỉ dùng cho AI và My StockRadar của chính bạn; không lưu số lượng cổ phiếu, NAV hoặc tài khoản môi giới.", "chỉ dùng cho tài khoản của bạn."),
        ("Sau khi thêm mã, có thể bật “Cảnh báo mã này” ngay trên từng dòng. Action Alert qua email vẫn cần quyền Premium và công tắc email toàn cục.", "Có thể bật cảnh báo trên từng mã."),
        ("Quyền truy cập:", "Bảo mật:"),
        ("hồ sơ, tùy chọn email, watchlist và dữ liệu vị thế tự khai báo được bảo vệ bằng Supabase RLS. Các dữ liệu này không được đưa vào nội dung công khai hoặc email của người khác.", "dữ liệu cá nhân được bảo vệ bằng Supabase RLS."),
        ("Xóa vĩnh viễn tài khoản StockRadar, hồ sơ và dữ liệu liên kết. Hành động này không thể hoàn tác và cần xác minh lại mật khẩu hiện tại.", "Xóa vĩnh viễn tài khoản và dữ liệu liên kết."),
    )
    for before, after in replacements:
        source = source.replace(before, after)
    return source


def process_page(output: Path, route: str) -> None:
    page = output / "index.html" if route == "" else output / route / "index.html"
    source = normalize_footer(normalize_header_register(normalize_nav(inject_style(read(page)), route)))
    transforms = {"": commercial_home, "hom-nay": commercial_today, "radar5": commercial_radar, "kiem-tra-co-phieu": commercial_lookup, "khuyen-nghi": commercial_recommendations, "nganh": commercial_sectors, "hieu-qua": commercial_performance, "dang-ky": commercial_plans, "tai-khoan": commercial_account}
    write(page, transforms[route](source))


def verify(output: Path) -> None:
    pages = {route: read(output / "index.html" if route == "" else output / route / "index.html") for route in CORE_ROUTES}
    for marker in ("data-stockradar-ai-center", "TOP CỔ PHIẾU", "commercial-proof-bar", "Email tự động báo điểm mua/bán"):
        if marker not in pages[""]:
            raise RuntimeError(f"Commercial homepage missing: {marker}")
    forbidden = {
        "": ("buyer-first-section", "email-mini home-email-form"),
        "radar5": ("radar-methodology", "operations-shortcuts"),
        "kiem-tra-co-phieu": ("conversion-rail", "Decision Feed đạt gate"),
        "khuyen-nghi": ("buyer-recommendation-contract", "recommendation-reference-note", "conversion-rail"),
        "nganh": ("conversion-rail", "30 cổ phiếu HOSE", "3 mã mỗi ngành"),
        "hieu-qua": ("buyer-first-section", "conversion-rail"),
        "dang-ky": ("conversion-plan-value", "buyer-plan-value", "premium-notify-title", "199K/tháng", "email-interest.js"),
        "tai-khoan": ("my-stockradar-hero",),
    }
    for route, markers in forbidden.items():
        for marker in markers:
            if marker in pages[route]:
                raise RuntimeError(f"Commercial {route or 'homepage'} still contains verbose marker: {marker}")
    for route, source in pages.items():
        if STYLE_MARKER not in source or COMMERCIAL_RUNTIME_MARKER not in source or COMMERCIAL_SCRIPT_NAME not in source:
            raise RuntimeError(f"Commercial bundle missing from {route or 'home'}")
        if NOTIFICATION_MARKER not in source or NOTIFICATION_SCRIPT_NAME not in source:
            raise RuntimeError(f"Notification bell bundle missing from {route or 'home'}")
    if "0đ</strong><span>/ tháng" in pages["dang-ky"]:
        raise RuntimeError("Free plan still contains monthly period copy")
    print("Commercial surface v1: PASS (AI → signals → proof → pricing; compact runtime + notification bell enabled)")


def main() -> None:
    output = parse_args().output.resolve()
    if not output.is_dir():
        raise RuntimeError(f"Pages output does not exist: {output}")
    for asset in (STYLE_NAME, COMMERCIAL_SCRIPT_NAME, NOTIFICATION_STYLE_NAME, NOTIFICATION_SCRIPT_NAME):
        if not (output / "assets" / asset).is_file():
            raise RuntimeError(f"Missing commercial asset: {asset}")
    for route in CORE_ROUTES:
        process_page(output, route)
    injected = inject_notification_assets_all(output)
    verify(output)
    print(f"StockRadar notification bell injected into {injected} auth-aware page(s)")


if __name__ == "__main__":
    main()
