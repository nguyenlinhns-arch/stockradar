#!/usr/bin/env python3
"""Apply conversion-first StockRadar surfaces after the standard product guards.

This layer does not open data, email, or billing gates. It only improves the buyer journey:
lookup first, contextual Premium preview, shorter pricing/signup, proof-first performance,
and a My StockRadar account surface. Checkout remains fail-closed unless its gate is ready.
"""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path


ASSET_MARKER = "data-conversion-v3"


def enabled(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    return parser.parse_args()


def inject_assets(source: str) -> str:
    if ASSET_MARKER in source or "</head>" not in source:
        return source
    assets = (
        f'<link rel="stylesheet" href="assets/conversion-v3.css?v=20260904-conv3" {ASSET_MARKER}>\n'
        '<script src="assets/conversion-v3.js?v=20260904-conv3" defer></script>\n'
    )
    return source.replace("</head>", assets + "</head>", 1)


def transform_home(source: str) -> str:
    source = source.replace("BẢNG ĐIỀU HÀNH · RA QUYẾT ĐỊNH TRÊN HOSE", "TRA CỨU QUYẾT ĐỊNH TRÊN HOSE")
    source = source.replace("<h1>StockRadar — từ dữ liệu đến hành động</h1>", "<h1>Bạn đang quan tâm mã nào?</h1>")
    source = re.sub(
        r'<p class="stock-analysis-intro">.*?</p>',
        '<p class="stock-analysis-intro">Nhập mã HOSE để xem ngay <strong>MUA hay CHỜ</strong>. Khi cần quyết định đầy đủ, Premium mở trạng thái vị thế, vùng mua, Stop, Target và cảnh báo thay đổi.</p>',
        source,
        count=1,
        flags=re.DOTALL,
    )
    source = source.replace(
        '<span class="data-pill">FREE: BIẾT BỐI CẢNH · PREMIUM: BIẾT HÀNH ĐỘNG</span>',
        '<span class="data-pill">HOSE · 4 KHUNG · KHÔNG CẦN TÀI KHOẢN CHỨNG KHOÁN</span>',
    )
    source = re.sub(
        r'\s*<article class="home-lead-card[^\"]*"[^>]*>.*?</article>',
        "",
        source,
        count=1,
        flags=re.DOTALL,
    )
    source = source.replace('class="home-command-row"', 'class="home-command-row conversion-search-only"', 1)
    source = source.replace(">Xem mã này</button>", '>Tra mã miễn phí</button>', 1)
    source = source.replace(
        '<button class="button button-primary" type="submit">Tra mã miễn phí</button>',
        '<button class="button button-primary" type="submit" data-conversion-action="home_lookup">Tra mã miễn phí</button>',
        1,
    )
    trust = '''<div class="conversion-hero-trust" aria-label="Cam kết khi tra cứu"><span>Miễn phí để bắt đầu</span><span>Không cần tài khoản chứng khoán</span><span>Không yêu cầu OTP môi giới</span></div>'''
    marker = '<div class="home-value-strip" aria-label="Giá trị cốt lõi StockRadar">'
    if trust not in source and marker in source:
        source = source.replace(marker, trust + "\n        " + marker, 1)
    return inject_assets(source)


def premium_cta(checkout_ready: bool) -> tuple[str, str, str]:
    if checkout_ready:
        return (
            "signup/?plan=premium&next=thanh-toan/%3Fplan%3Dpremium",
            "Mở Premium 30 ngày · 199.000đ",
            "Không tự gia hạn. Thanh toán chỉ ở bước riêng sau khi tài khoản được xác minh.",
        )
    return (
        "signup/?plan=premium",
        "Tạo tài khoản Premium",
        "Cổng thanh toán chưa mở — tạo tài khoản không phát sinh thu phí.",
    )


def transform_stock(source: str, *, checkout_ready: bool) -> str:
    href, label, note = premium_cta(checkout_ready)
    source = source.replace("Phân tích Free & Premium — StockRadar", "Tra cứu & quyết định — StockRadar")
    source = source.replace("<span>Phân tích</span><h1>Phân tích cổ phiếu</h1>", "<span>Quyết định</span><h1>Mã này nên làm gì?</h1>")
    source = source.replace(
        'aria-label="Bốn đầu ra chính của phân tích StockRadar"',
        'aria-label="Bốn đầu ra chính của StockRadar"',
    )
    premium = f'''<aside class="analysis-tier-card analysis-tier-premium premium-preview-v3" aria-labelledby="premium-analysis-title">
            <div class="premium-live-report-slot" data-premium-stock-report hidden></div>
            <div data-premium-gate-copy>
              <header class="premium-preview-head"><div><span class="analysis-tier-badge is-premium">BẢN XEM TRƯỚC PREMIUM</span><h2 id="premium-analysis-title">Mở quyết định đầy đủ cho mã bạn vừa tra</h2><p>Free cho bạn bối cảnh. Premium mở phần trực tiếp phục vụ hành động và quản trị rủi ro.</p></div><span class="premium-preview-badge">199K / 30 NGÀY</span></header>
              <div class="premium-preview-grid" aria-label="Các đầu ra Premium">
                <div class="premium-preview-field is-locked"><span>Mua mới?</span><strong class="premium-preview-lock">MUA / CHỜ</strong></div>
                <div class="premium-preview-field is-locked"><span>Đang nắm giữ?</span><strong class="premium-preview-lock">GIỮ / TĂNG / GIẢM / BÁN</strong></div>
                <div class="premium-preview-field is-locked"><span>Vùng mua</span><strong class="premium-preview-lock">Mở Premium</strong></div>
                <div class="premium-preview-field is-locked"><span>Stop / vô hiệu</span><strong class="premium-preview-lock">Mở Premium</strong></div>
                <div class="premium-preview-field is-locked"><span>Target</span><strong class="premium-preview-lock">Mở Premium</strong></div>
                <div class="premium-preview-field"><span>Cảnh báo thay đổi</span><strong>10:30 · 11:15 · 13:30 · 14:15</strong></div>
              </div>
              <div class="premium-preview-promise"><strong>Không khóa giá trị Free.</strong> Bạn vẫn xem được bối cảnh để tự đánh giá; Premium chỉ khóa phần trực tiếp giúp ra quyết định và theo dõi thay đổi.</div>
              <div class="premium-preview-actions"><a class="button button-primary" href="{href}" data-premium-conversion-cta data-conversion-action="stock_premium">{label}</a><a class="button button-secondary" href="hieu-qua/" data-conversion-action="stock_proof">Xem hiệu quả trước</a></div>
              <span class="premium-preview-price">{note}</span>
              <div class="premium-preview-trust"><span>Không tự đặt lệnh</span><span>Không cần mật khẩu/OTP môi giới</span><span>Không cam kết lợi nhuận</span></div>
            </div>
          </aside>'''
    source, count = re.subn(
        r'<aside class="analysis-tier-card analysis-tier-premium"[^>]*>.*?</aside>',
        premium,
        source,
        count=1,
        flags=re.DOTALL,
    )
    if count != 1 and "premium-preview-v3" not in source:
        raise RuntimeError("Stock Premium surface not found")
    source = source.replace("Phân tích cơ bản · Bối cảnh để tự đánh giá", "Bối cảnh Free để tự đánh giá")
    source = source.replace("Tra cứu mã, Radar 30, bối cảnh ngành và bốn khung đầu tư.", "Tra cứu mã, bối cảnh ngành và bốn khung đầu tư.")
    source = source.replace("✓ Radar 30 & theo ngành", "✓ Radar & theo ngành")
    return inject_assets(source)


def transform_plans(source: str, *, checkout_ready: bool) -> str:
    href, label, note = premium_cta(checkout_ready)
    source = re.sub(
        r'<h1>Free để biết thị trường\.<br>Premium để biết mình nên làm gì\.</h1>',
        '<h1>Premium 199.000đ / 30 ngày.<br>Trả tiền cho quyết định, không trả tiền cho thuật ngữ.</h1>',
        source,
        count=1,
    )
    source = re.sub(
        r'<section class="buyer-plan-value" aria-labelledby="buyer-plan-title">.*?</section>',
        '''<section class="conversion-plan-value" aria-labelledby="buyer-plan-title"><span class="panel-label">PREMIUM CÓ GIÁ TRỊ Ở ĐÂU?</span><h2 id="buyer-plan-title">Bốn thứ trực tiếp giúp bạn ra quyết định.</h2><p>Free đủ để xem và tự đánh giá. Premium đáng tiền khi bạn cần câu trả lời hành động, vùng giá, kiểm soát rủi ro và được báo khi quyết định thay đổi.</p><div class="conversion-plan-grid"><div><strong>1 · Quyết định</strong><span>MUA / CHỜ hoặc GIỮ / TĂNG / GIẢM / BÁN.</span></div><div><strong>2 · Vùng hành động</strong><span>Vùng mua · Stop · Target · Risk/Reward.</span></div><div><strong>3 · Cảnh báo</strong><span>Báo khi trạng thái thay đổi tại các mốc rà soát trong phiên.</span></div><div><strong>4 · Kiểm chứng</strong><span>Nhật ký có dấu thời gian và hiệu quả để tự đối chiếu.</span></div></div></section>''',
        source,
        count=1,
        flags=re.DOTALL,
    )
    premium_card = f'''<article class="plan-card plan-card-premium conversion-plan-card" data-plan-premium id="premium">
            <span class="plan-ribbon">LỚP QUYẾT ĐỊNH</span><span class="plan-kicker">PREMIUM</span><h2>StockRadar Premium</h2><div class="plan-price"><strong>199.000đ</strong><span>/ 30 ngày</span></div>
            <p class="plan-summary">Dành cho người muốn biết <strong>nên làm gì, ở vùng giá nào và khi nào phải thay đổi quyết định</strong>.</p>
            <ul class="plan-feature-list"><li><strong>Mua mới:</strong> MUA / CHỜ theo từng khung.</li><li><strong>Đang nắm giữ:</strong> GIỮ / TĂNG / GIẢM / BÁN.</li><li><strong>Vùng hành động:</strong> Vùng mua · tỷ trọng · Stop · Target · Risk/Reward.</li><li><strong>Cảnh báo thay đổi:</strong> 10:30 · 11:15 · 13:30 · 14:15 khi đủ điều kiện.</li><li><strong>My StockRadar:</strong> watchlist mở rộng và ưu tiên mã bạn quan tâm.</li><li><strong>Kiểm chứng:</strong> lịch sử, trạng thái và kết quả có dấu thời gian.</li></ul>
            <a class="button button-primary" href="{href}" data-premium-conversion-cta data-conversion-action="plans_premium">{label}</a><p class="conversion-plan-note">{note}</p>
          </article>'''
    source, count = re.subn(
        r'<article class="plan-card plan-card-premium"[^>]*>.*?</article>',
        premium_card,
        source,
        count=1,
        flags=re.DOTALL,
    )
    if count != 1 and "conversion-plan-card" not in source:
        raise RuntimeError("Premium plan card not found")
    source = re.sub(r'<p class="plan-price-note">Giá sáng lập dự kiến;.*?</p>', "", source, flags=re.DOTALL)
    return inject_assets(source)


def transform_signup(source: str) -> str:
    source = source.replace(
        "Free nhận bản tin 09:00.<br>Premium thêm cảnh báo trong phiên.",
        "Tạo tài khoản trong một bước.<br>Chọn Premium khi bạn cần hành động.",
    )
    source = re.sub(
        r'<p>Gói Free dành cho người muốn theo dõi thị trường mỗi ngày\..*?</p>',
        '<p>Nếu bạn đi từ một mã vừa tra, lựa chọn Premium được giữ sẵn. Tạo tài khoản không tự phát sinh thanh toán.</p>',
        source,
        count=1,
        flags=re.DOTALL,
    )
    summary = '''<div class="conversion-premium-summary" data-premium-flow-summary hidden><strong>Bạn đang đăng ký StockRadar Premium · 199.000đ/30 ngày</strong><span>Bước này chỉ tạo và xác minh tài khoản. Không tự thu phí, không tự gia hạn.</span></div>'''
    marker = '<form class="auth-form" data-auth-signup-form novalidate>'
    if summary not in source and marker in source:
        source = source.replace(marker, summary + "\n        " + marker, 1)
    source = source.replace("<legend>Email StockRadar</legend>", "<legend>Tùy chọn nhận email</legend>")
    return inject_assets(source)


def transform_performance(source: str) -> str:
    source = source.replace("PHƯƠNG PHÁP ĐO NHẤT QUÁN", "KẾT QUẢ · CÓ DẤU THỜI GIAN")
    buyer = re.search(r'\s*<section class="buyer-first-section".*?</section>', source, flags=re.DOTALL)
    perf = re.search(r'\s*<section class="performance-workspace".*?</section>', source, flags=re.DOTALL)
    if buyer and perf and buyer.start() < perf.start():
        buyer_html, perf_html = buyer.group(0), perf.group(0)
        perf_html = perf_html.replace(
            '<section class="performance-workspace"><div class="container">',
            '<section class="performance-workspace"><div class="container"><div class="conversion-performance-head"><span class="panel-label">KẾT QUẢ TRƯỚC, CÁCH ĐO SAU</span><h2>Hãy nhìn dữ liệu thực tế trước khi quyết định trả phí.</h2><p>Chỉ số hiệu quả bên dưới chỉ xuất hiện từ dữ liệu đủ điều kiện phát hành. Nếu chưa đủ mẫu, StockRadar phải nói rõ thay vì suy diễn.</p><div class="conversion-performance-trust"><span>Không cherry-pick</span><span>Không tính tín hiệu chưa kích hoạt như đã mua</span><span>So cùng cửa sổ với VN-Index</span></div></div>',
            1,
        )
        source = source[: buyer.start()] + perf_html + "\n\n" + buyer_html + source[perf.end() :]
    elif "conversion-performance-head" not in source:
        raise RuntimeError("Performance sections not found")
    return inject_assets(source)


def transform_account(source: str) -> str:
    source = source.replace("Tài khoản & Email — StockRadar", "My StockRadar — Tài khoản")
    source = source.replace("<h1>Tài khoản StockRadar</h1><p>Quản lý email báo cáo, cảnh báo mua/bán, danh sách theo dõi và bảo mật.</p>", "<h1>My StockRadar</h1><p>Các mã bạn quan tâm, trạng thái vị thế, cảnh báo và tùy chọn tài khoản ở một nơi.</p>")
    hero = '''<section class="my-stockradar-hero" aria-labelledby="my-stockradar-title"><div class="my-stockradar-hero-head"><div><span class="panel-label">MY STOCKRADAR</span><h2 id="my-stockradar-title">Biến watchlist thành trung tâm quyết định cá nhân.</h2><p>Thêm mã bạn quan tâm, đánh dấu đang sở hữu hay chưa và bật cảnh báo từng mã. Khi quyền Premium hoạt động, hệ thống ưu tiên đúng các mã này.</p></div><a class="button button-primary" href="kiem-tra-co-phieu/" data-conversion-action="account_lookup">Tra thêm mã</a></div><div class="my-stockradar-grid"><div><strong>Watchlist</strong><span>Mã bạn thực sự quan tâm.</span></div><div><strong>Đang sở hữu?</strong><span>Tách góc nhìn vị thế khỏi mua mới.</span></div><div><strong>Cảnh báo từng mã</strong><span>Chỉ nhận thay đổi bạn muốn theo dõi.</span></div><div><strong>Khung ưu tiên</strong><span>Ngắn · trung · dài · tích sản.</span></div></div></section>'''
    marker = '<div data-auth-account-details hidden>'
    if hero not in source and marker in source:
        source = source.replace(marker, marker + "\n        " + hero, 1)
    source = source.replace("CÁ NHÂN HÓA", "MY STOCKRADAR")
    source = source.replace("ƯU TIÊN PHÂN TÍCH", "ƯU TIÊN THEO DÕI")
    return inject_assets(source)


def transform_recommendations(source: str, *, checkout_ready: bool) -> str:
    href, label, _ = premium_cta(checkout_ready)
    upgrade = f'''<div class="conversion-inline-upgrade"><div><strong>Muốn nhận các thay đổi này cho chính watchlist của bạn?</strong><span>Premium ưu tiên mã bạn theo dõi và mở vùng mua, Stop, Target cùng cảnh báo trạng thái.</span></div><a class="button button-primary" href="{href}" data-premium-conversion-cta data-conversion-action="recommendation_premium">{label}</a></div>'''
    if upgrade not in source:
        contract = re.search(r'<section class="buyer-recommendation-contract".*?</section>', source, flags=re.DOTALL)
        if contract:
            source = source[: contract.end()] + "\n      " + upgrade + source[contract.end() :]
    return inject_assets(source)


def transform_checkout(source: str) -> str:
    source = source.replace("Thanh toán đơn giản.<br>Kích hoạt sau khi giao dịch được xác minh.", "Premium 30 ngày.<br>Một lần thanh toán.")
    source = source.replace(
        "Một lần thanh toán cho 30 ngày Premium. Không tự gia hạn. Sau khi giao dịch được xác minh, quyền Premium được cộng vào tài khoản StockRadar.",
        "199.000đ cho 30 ngày Premium. Không tự gia hạn. Quyền chỉ được kích hoạt sau khi giao dịch được xác minh.",
    )
    source = re.sub(
        r'<ul class="checkout-features">.*?</ul>',
        '<ul class="checkout-features"><li>MUA / CHỜ và GIỮ / TĂNG / GIẢM / BÁN.</li><li>Vùng mua · Stop · Target · Risk/Reward.</li><li>Cảnh báo thay đổi tại các mốc rà soát trong phiên.</li><li>My StockRadar: watchlist và nhật ký để kiểm chứng.</li></ul>',
        source,
        count=1,
        flags=re.DOTALL,
    )
    source = source.replace(
        '<div class="checkout-price"><strong data-checkout-amount>199.000đ</strong><span>/ 30 ngày</span></div>',
        '<div class="checkout-price"><strong data-checkout-amount>199.000đ</strong><span>/ 30 ngày</span></div><div class="conversion-checkout-summary"><strong>Không tự gia hạn</strong><span>Không yêu cầu mật khẩu/OTP môi giới. Không cam kết lợi nhuận.</span></div>',
        1,
    )
    return inject_assets(source)


def transform_file(path: Path, *, checkout_ready: bool) -> None:
    if not path.is_file():
        return
    source = path.read_text(encoding="utf-8")
    relative = path.as_posix()
    if relative.endswith("/index.html") or path.name == "index.html":
        pass
    if path.parent.name == "co-phieu":
        source = transform_stock(source, checkout_ready=checkout_ready)
    elif path.parent.name == "dang-ky":
        source = transform_plans(source, checkout_ready=checkout_ready)
    elif path.parent.name == "signup":
        source = transform_signup(source)
    elif path.parent.name == "hieu-qua":
        source = transform_performance(source)
    elif path.parent.name == "tai-khoan":
        source = transform_account(source)
    elif path.parent.name == "khuyen-nghi":
        source = transform_recommendations(source, checkout_ready=checkout_ready)
    elif path.parent.name == "thanh-toan":
        source = transform_checkout(source)
    path.write_text(source, encoding="utf-8")


def main() -> None:
    output = parse_args().output.resolve()
    if not output.is_dir():
        raise RuntimeError(f"Pages output does not exist: {output}")
    for asset in ("conversion-v3.css", "conversion-v3.js"):
        if not (output / "assets" / asset).is_file():
            raise RuntimeError(f"Missing conversion asset: {asset}")

    checkout_ready = enabled("STOCKRADAR_CHECKOUT_READY")
    home = output / "index.html"
    if not home.is_file():
        raise RuntimeError("Homepage missing")
    home.write_text(transform_home(home.read_text(encoding="utf-8")), encoding="utf-8")

    for route in ("co-phieu", "dang-ky", "signup", "hieu-qua", "tai-khoan", "khuyen-nghi", "thanh-toan"):
        transform_file(output / route / "index.html", checkout_ready=checkout_ready)

    print(f"Conversion v3 surfaces: PASS (checkout_ready={str(checkout_ready).lower()})")


if __name__ == "__main__":
    main()
