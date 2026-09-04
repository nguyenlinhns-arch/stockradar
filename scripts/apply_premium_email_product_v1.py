#!/usr/bin/env python3
"""Apply buyer-facing Premium email product surfaces without opening delivery gates."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


CSS_TAG = '<link rel="stylesheet" href="assets/premium-email-product-v1.css?v=20260904-emailprod1" data-premium-email-product-v1>\n'

HOME_EMAIL_BLOCK = '''<div class="home-premium-email-v1" data-premium-email-product-v1>
              <span class="panel-label">EMAIL LÀ CÁCH PREMIUM GIAO GIÁ TRỊ</span>
              <h3>Không cần mở StockRadar liên tục.</h3>
              <p>StockRadar được thiết kế để đưa thay đổi đáng chú ý của đúng các mã bạn theo dõi tới email, thay vì bắt bạn tự kiểm tra lại từng mã nhiều lần trong ngày.</p>
              <div class="home-premium-email-steps">
                <div class="home-premium-email-step"><strong>09:00 · Watchlist trước</strong><span>Biết mã nào của bạn cần chú ý; thị trường chỉ là phần bối cảnh sau đó.</span></div>
                <div class="home-premium-email-step"><strong>Trong phiên · Chỉ khi đổi trạng thái</strong><span>CHỜ → MUA, GIỮ → GIẢM/BÁN hoặc thay đổi quan trọng khác mới tạo Action Alert.</span></div>
                <div class="home-premium-email-step"><strong>Không đổi · Không spam</strong><span>Không có thay đổi đủ mức hành động thì không tạo email cảnh báo riêng chỉ để tăng số lượng.</span></div>
              </div>
              <span class="home-premium-email-rule">Email chỉ được gửi khi tài khoản, consent, quyền gói và hệ thống delivery đều đủ điều kiện.</span>
            </div>'''

SIGNUP_BLOCK = '''<div class="premium-email-onboarding-v1" data-premium-email-onboarding>
          <span class="panel-label">KÍCH HOẠT GIÁ TRỊ PREMIUM</span>
          <h3>Để StockRadar canh mã thay bạn.</h3>
          <p>Sau khi tài khoản được xác minh, hãy thêm watchlist và bật email cho đúng loại thông tin bạn muốn nhận. Không mục email nào được tự chọn thay bạn.</p>
          <div class="premium-email-onboarding-steps">
            <span><b>1.</b> Xác minh email StockRadar.</span>
            <span><b>2.</b> Thêm mã, khung đầu tư và đánh dấu mã đang sở hữu.</span>
            <span><b>3.</b> Bật Action Alert cho những mã thực sự cần StockRadar theo dõi.</span>
          </div>
        </div>'''

HEALTH_BLOCK = '''<section class="premium-email-health-v1" data-premium-email-health aria-labelledby="premium-email-health-title">
          <article class="premium-email-health-card">
            <header class="premium-email-health-head"><div><span class="panel-label">SỨC KHỎE EMAIL PREMIUM</span><h2 id="premium-email-health-title">StockRadar có đang canh email cho bạn không?</h2><p>Kiểm tra nhanh cấu hình theo dõi và lần giao email gần nhất của chính tài khoản này.</p></div><strong data-email-health-system>—</strong></header>
            <div class="premium-email-health-grid">
              <div><span>Gói / tài khoản</span><strong data-email-health-tier>—</strong></div>
              <div><span>Daily 09:00</span><strong data-email-health-daily>—</strong></div>
              <div><span>Action Alert</span><strong data-email-health-alerts>—</strong></div>
              <div><span>Watchlist</span><strong data-email-health-watchlist>—</strong></div>
              <div><span>Mã bật cảnh báo</span><strong data-email-health-tickers>—</strong></div>
              <div><span>Email gần nhất</span><strong data-email-health-last>—</strong></div>
            </div>
            <p class="premium-email-health-note" data-email-health-note>Chỉ hiển thị metadata vận hành của chính tài khoản; không hiển thị provider secret hoặc nội dung email.</p>
          </article>
        </section>'''

OPTIONAL_CHOICES = '''
                <label class="email-choice is-optional-premium"><input type="checkbox" name="post_session_digest"><span><span class="email-choice-badge">Premium · tùy chọn</span><strong>Tóm tắt cuối phiên</strong><span>Gom các thay đổi mới/đóng/hết hiệu lực sau phiên. Không cần bật nếu bạn chỉ muốn Daily và Action Alert.</span></span></label>
                <label class="email-choice is-optional-premium"><input type="checkbox" name="weekly_report"><span><span class="email-choice-badge">Premium · tùy chọn</span><strong>Tổng kết tuần</strong><span>Xem lại thay đổi trạng thái và lịch sử đã ghi nhận trong tuần; có thể tắt riêng mà không ảnh hưởng Action Alert.</span></span></label>'''


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    return parser.parse_args()


def inject_css(source: str) -> str:
    if "premium-email-product-v1.css" in source:
        return source
    if "</head>" not in source:
        return source
    return source.replace("</head>", CSS_TAG + "</head>", 1)


def transform_home(source: str) -> str:
    marker = '          </div>\n          <aside class="home-premium-buybox">'
    if HOME_EMAIL_BLOCK not in source:
        if marker not in source:
            raise RuntimeError("Premium homepage buybox marker missing")
        source = source.replace(marker, f"            {HOME_EMAIL_BLOCK}\n          </div>\n          <aside class=\"home-premium-buybox\">", 1)
    source = source.replace(
        '>Theo dõi mã của tôi</a>',
        '>Theo dõi mã của tôi &amp; nhận email</a>',
        1,
    )
    return inject_css(source)


def transform_signup(source: str) -> str:
    if SIGNUP_BLOCK not in source:
        marker = '<div class="conversion-premium-summary"'
        pos = source.find(marker)
        if pos < 0:
            marker = '<form class="auth-form" data-auth-signup-form'
            pos = source.find(marker)
        if pos < 0:
            raise RuntimeError("Signup form marker missing")
        source = source[:pos] + SIGNUP_BLOCK + "\n        " + source[pos:]

    replacements = (
        (
            'Tạo tài khoản StockRadar Free để nhận bản rà soát 09:00 hoặc chọn Premium để thêm cảnh báo điểm mua/bán trong phiên.',
            'Tạo tài khoản StockRadar Free hoặc ghi nhận nhu cầu Premium. Free dùng các chức năng công khai; Daily 09:00 và Action Alert thuộc Trial/Premium.',
        ),
        (
            'Free nhận bản tin 09:00.<br>Premium thêm cảnh báo trong phiên.',
            'Free để tra cứu.<br>Premium để nhận lớp quyết định.',
        ),
        (
            'Gói Free dành cho người muốn theo dõi thị trường mỗi ngày. Premium kế thừa quyền Free và bổ sung phân tích chuyên sâu, kế hoạch giao dịch cùng cảnh báo điểm mua/bán khi tín hiệu đạt chuẩn.',
            'Gói Free dành cho người muốn dùng các chức năng công khai và tự đánh giá. Premium bổ sung Daily 09:00, kế hoạch giao dịch và cảnh báo hành động khi dữ liệu đủ chuẩn.',
        ),
        (
            '<span class="auth-step"><b>3</b>Nhận email theo quyền gói</span>',
            '<span class="auth-step"><b>3</b>Kích hoạt quyền theo gói</span>',
        ),
        (
            '<li><strong>Free:</strong> 0đ, tra cứu mã HOSE, Radar/phân tích công khai, danh sách theo dõi cơ bản và <strong>bản rà soát thị trường lúc 09:00 mỗi ngày</strong> sau khi email được xác minh và bạn đồng ý nhận.</li>',
            '<li><strong>Free:</strong> 0đ, tra cứu mã HOSE, Radar/phân tích công khai, danh sách theo dõi cơ bản và email hệ thống cần thiết cho tài khoản.</li>',
        ),
        (
            '<li><strong>Premium trả phí:</strong> toàn bộ quyền Free + phân tích sâu, Buy Zone/Stop/Target/R:R và <strong>cảnh báo điểm mua/bán trong phiên</strong> tại 10:30, 11:15, 13:30, 14:15 khi tín hiệu đủ chuẩn.</li>',
            '<li><strong>Premium trả phí:</strong> toàn bộ quyền Free + Daily 09:00, phân tích sâu, Buy Zone/Stop/Target/R:R và <strong>cảnh báo điểm mua/bán trong phiên</strong> tại 10:30, 11:15, 13:30, 14:15 khi tín hiệu đủ chuẩn.</li>',
        ),
        (
            '<span>Tra cứu, Radar, phân tích công khai và bản rà soát 09:00 hằng ngày.</span>',
            '<span>Tra cứu, Radar, phân tích công khai và watchlist cơ bản.</span>',
        ),
        (
            '<span>Toàn bộ Free + phân tích sâu và cảnh báo điểm mua/bán trong phiên.</span>',
            '<span>Daily 09:00 + phân tích sâu + kế hoạch giao dịch + Action Alert.</span>',
        ),
        (
            'Free có phí 0đ và có quyền nhận bản rà soát 09:00 sau khi xác minh email và đồng ý nhận.',
            'Free có phí 0đ, dùng chức năng công khai và chỉ nhận email hệ thống cần thiết cho tài khoản.',
        ),
        (
            '<legend>Email StockRadar</legend>',
            '<legend>Email Premium StockRadar</legend>',
        ),
        (
            '<label class="auth-check"><input name="email_daily_brief" type="checkbox"><span><strong>Bản rà soát StockRadar lúc 09:00 hằng ngày</strong> <span class="email-choice-badge">FREE + PREMIUM</span> — tổng quan thị trường, cổ phiếu/ngành nổi bật ở mức phù hợp với quyền gói. Chọn mục này để nhận email sau khi xác minh.</span></label>',
            '<label class="auth-check"><input name="email_daily_brief" type="checkbox" disabled><span><strong>Daily 09:00</strong> <span class="email-choice-badge">PREMIUM</span> — ưu tiên watchlist và việc cần chú ý trước bối cảnh thị trường. Chỉ ghi nhận nhu cầu khi bạn chọn Premium.</span></label>',
        ),
        (
            '<label class="auth-check"><input name="email_event_alerts" type="checkbox"><span><strong>Cảnh báo điểm mua/bán trong phiên</strong> <span class="email-choice-badge">PREMIUM</span> — thông báo khi có hành động được xác nhận như đạt điểm mua, nhồi lệnh, hạ tỷ trọng hoặc cắt lỗ/bán.</span></label>',
            '<label class="auth-check"><input name="email_event_alerts" type="checkbox" disabled><span><strong>Cảnh báo điểm mua/bán trong phiên</strong> <span class="email-choice-badge">PREMIUM</span> — thông báo khi có hành động được xác nhận như đạt điểm mua, nhồi lệnh, hạ tỷ trọng hoặc cắt lỗ/bán.</span></label>',
        ),
        (
            'Không có email nội dung nào được bật nếu bạn chưa đồng ý nhận. Free đủ quyền nhận bản 09:00; cảnh báo mua/bán chỉ được gửi khi tài khoản có quyền Trial/Paid, email đã xác minh và có đồng ý nhận hợp lệ.',
            'Hai lựa chọn này chỉ dành cho Trial/Paid. Chọn Premium ở trên để ghi nhận nhu cầu; quyền gửi thực tế vẫn cần tài khoản đủ quyền, email đã xác minh, consent hợp lệ và hệ thống delivery được kích hoạt.',
        ),
        (
            'Sau khi xác minh, Free có thể nhận bản tin 09:00 theo lựa chọn; cảnh báo điểm mua/bán chỉ kích hoạt khi tài khoản có quyền Premium.',
            'Sau khi xác minh, Free dùng tài khoản bình thường; các email nội dung chỉ có hiệu lực khi tài khoản được cấp quyền Trial/Paid và hệ thống gửi đủ điều kiện.',
        ),
        (
            'assets/signup-email-intent.js?v=20260904-privacy1',
            'assets/signup-email-intent.js?v=20260904-paid2',
        ),
    )
    for old, new in replacements:
        source = source.replace(old, new)

    if '<a href="hom-nay/">Hôm nay</a>' not in source:
        source = source.replace(
            '<nav class="nav-links" id="site-menu" aria-label="Điều hướng chính" data-nav-menu><a href="radar5/">',
            '<nav class="nav-links" id="site-menu" aria-label="Điều hướng chính" data-nav-menu><a href="hom-nay/">Hôm nay</a><a href="radar5/">',
            1,
        )
    return inject_css(source)


def transform_account(source: str) -> str:
    if HEALTH_BLOCK not in source:
        marker = '<section class="account-email-center" data-product-email-preferences'
        pos = source.find(marker)
        if pos < 0:
            raise RuntimeError("Account email center marker missing")
        source = source[:pos] + HEALTH_BLOCK + "\n\n        " + source[pos:]

    choice_pattern = re.compile(
        r'(<div class="email-choice-list">.*?<label class="email-choice"><input type="checkbox" name="event_alerts".*?</label>)(\s*</div>)',
        flags=re.DOTALL,
    )
    if 'name="post_session_digest"' not in source:
        source, count = choice_pattern.subn(r"\1" + OPTIONAL_CHOICES + r"\2", source, count=1)
        if count != 1:
            raise RuntimeError("Account email choices marker missing")

    source = source.replace(
        'Gửi khi có hành động được xác nhận: đạt điểm mua, nhồi lệnh, hạ tỷ trọng, cắt lỗ/bán hoặc thay đổi trạng thái quan trọng.',
        'Chỉ gửi khi có thay đổi hành động được xác nhận. Không đổi trạng thái → không tạo Action Alert riêng.',
        1,
    )

    source = source.replace(
        'Free nhận bản rà soát cơ bản; Trial/Paid có thể nhận nội dung Premium và cảnh báo điểm mua/bán.',
        'Báo cáo hằng ngày và cảnh báo hành động dành cho Trial/Paid; Free chỉ nhận email hệ thống cần thiết cho tài khoản.',
    )
    source = source.replace(
        '<label class="email-choice"><input type="checkbox" name="daily_brief"><span><strong>Báo cáo StockRadar hằng ngày</strong><span>Bản rà soát thị trường cơ bản ở Free; nội dung sâu hơn ở Premium khi dữ liệu đủ điều kiện phát hành.</span></span></label>',
        '<label class="email-choice"><input type="checkbox" name="daily_brief"><span><span class="email-choice-badge">Premium</span><strong>Báo cáo StockRadar hằng ngày</strong><span>Daily 09:00 ưu tiên watchlist, việc cần chú ý và bối cảnh thị trường khi dữ liệu đủ điều kiện phát hành.</span></span></label>',
    )
    source = source.replace(
        'Cần email đã xác minh. Ở Free, công tắc này chỉ kích hoạt bản tin hằng ngày; cảnh báo mua/bán chỉ có hiệu lực khi tài khoản có quyền Premium.',
        'Cần email đã xác minh và tài khoản Trial/Paid. Mỗi loại email có thể bật/tắt riêng; hệ thống delivery vẫn phải đủ điều kiện mới gửi.',
    )
    source = source.replace(
        'pattern="[A-Za-z]{3}" placeholder="VD: MBB"',
        'pattern="[A-Za-z0-9]{3}" placeholder="VD: MBB"',
    )
    source = source.replace(
        'assets/account-preferences.js?v=20260903-personalization1',
        'assets/account-preferences.js?v=20260904-paid2',
    )
    source = source.replace(
        'assets/email-preferences.js?v=20260903-email2',
        'assets/email-preferences.js?v=20260904-paid3',
    )
    if '<a href="hom-nay/">Hôm nay</a>' not in source:
        source = source.replace(
            '<nav class="nav-links" id="site-menu" aria-label="Điều hướng chính" data-nav-menu><a href="radar5/">',
            '<nav class="nav-links" id="site-menu" aria-label="Điều hướng chính" data-nav-menu><a href="hom-nay/">Hôm nay</a><a href="radar5/">',
            1,
        )
    return inject_css(source)


def main() -> None:
    output = parse_args().output.resolve()
    routes = {
        output / "index.html": transform_home,
        output / "signup" / "index.html": transform_signup,
        output / "tai-khoan" / "index.html": transform_account,
    }
    for path, transform in routes.items():
        if not path.is_file():
            raise RuntimeError(f"Premium email product route missing: {path}")
        source = path.read_text(encoding="utf-8")
        path.write_text(transform(source), encoding="utf-8")

    print("Premium email product v1: PASS (paid-only promise → onboarding → delivery health/control)")


if __name__ == "__main__":
    main()