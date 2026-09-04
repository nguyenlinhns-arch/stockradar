#!/usr/bin/env python3
"""Second commercial pass for stock detail, authentication and checkout surfaces.

Runs after v1 and preserves all functional hooks. It only removes/reduces buyer-facing
explanation and adds compact commercial classes/styles.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

STYLE_NAME = "commercial-v2.css"
STYLE_MARKER = "data-commercial-v2"
ROUTES = ("co-phieu", "signup", "dang-nhap", "thanh-toan")


def args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    return parser.parse_args()


def read(path: Path) -> str:
    if not path.is_file():
        raise RuntimeError(f"Commercial v2 target missing: {path}")
    return path.read_text(encoding="utf-8")


def write(path: Path, source: str) -> None:
    path.write_text(source, encoding="utf-8")


def inject_style(source: str) -> str:
    if STYLE_MARKER in source:
        return source
    if "</head>" not in source:
        raise RuntimeError("Commercial v2 target missing closing head")
    tag = f'<link rel="stylesheet" href="assets/{STYLE_NAME}?v=20260904-commercial2" {STYLE_MARKER}>'
    return source.replace("</head>", tag + "\n</head>", 1)


def add_body_class(source: str, class_name: str) -> str:
    if class_name in source:
        return source
    source, count = re.subn(
        r'<body([^>]*)>',
        lambda m: f'<body{m.group(1)[:-1]} class="{class_name}">' if m.group(1).rstrip().endswith('/') else _body_class(m.group(1), class_name),
        source,
        count=1,
        flags=re.I,
    )
    if count != 1:
        raise RuntimeError(f"Cannot add body class {class_name}")
    return source


def _body_class(attrs: str, class_name: str) -> str:
    class_match = re.search(r'class=["\']([^"\']*)["\']', attrs, flags=re.I)
    if class_match:
        updated = re.sub(
            r'class=["\']([^"\']*)["\']',
            lambda m: f'class="{m.group(1)} {class_name}"',
            attrs,
            count=1,
            flags=re.I,
        )
        return f'<body{updated}>'
    return f'<body{attrs} class="{class_name}">'


def remove_block(source: str, class_name: str, *, tag: str = "section", required: bool = False) -> str:
    pattern = re.compile(
        rf'\s*<{tag}\b[^>]*class=["\'][^"\']*\b{re.escape(class_name)}\b[^"\']*["\'][^>]*>.*?</{tag}>\s*',
        flags=re.I | re.S,
    )
    source, count = pattern.subn("\n", source, count=1)
    if required and count != 1:
        raise RuntimeError(f"Expected .{class_name}, found {count}")
    return source


def commercial_stock(source: str) -> str:
    source = add_body_class(source, "commercial-stock-page")
    source = source.replace(
        'Câu hỏi đầu tiên không phải “cổ phiếu này tốt không?”, mà là <strong>mua mới được chưa?</strong> và <strong>nếu đang nắm giữ thì nên làm gì?</strong>',
        'Mua mới · Đang nắm giữ · Vùng giá · Rủi ro.',
    )
    source = source.replace("FREE + PREMIUM", "STOCKRADAR")

    decision = '''<div class="buyer-decision-strip" aria-label="Đầu ra StockRadar"><div><strong>Mua mới</strong><span>MUA / CHỜ</span></div><div><strong>Đang nắm giữ</strong><span>GIỮ / TĂNG / GIẢM / BÁN</span></div><div><strong>Kế hoạch</strong><span>Buy Zone · Stop · Target · R/R</span></div><div><strong>Cảnh báo</strong><span>Khi trạng thái thay đổi</span></div></div>'''
    source, count = re.subn(r'<div class="buyer-decision-strip".*?</div>\s*<div class="analysis-tier-grid">', decision + '<div class="analysis-tier-grid">', source, count=1, flags=re.I | re.S)
    if count != 1:
        raise RuntimeError("Stock decision strip not found")

    source = source.replace("Phân tích cơ bản · Bối cảnh để tự đánh giá", "Free · Bối cảnh")
    source = source.replace("Tra cứu mã, Radar toàn HOSE, bối cảnh ngành và bốn khung đầu tư.", "Dữ liệu công khai để tự đánh giá.")
    source = re.sub(
        r'<div class="analysis-tier-entitlements">.*?</div>',
        '<div class="analysis-tier-entitlements"><span>✓ Tra cứu HOSE</span><span>✓ Radar</span><span>✓ Lịch sử hiệu quả</span></div>',
        source,
        count=1,
        flags=re.I | re.S,
    )
    source = source.replace("Lớp quyết định & kế hoạch hành động", "Premium · Quyết định")
    source = source.replace("Đầu ra ưu tiên quyết định trước, phương pháp và dữ liệu giải thích phía sau.", "Quyết định và kế hoạch hành động.")

    preview = '''<div data-premium-gate-copy><div class="commercial-premium-preview">
      <div class="commercial-premium-row"><span>Mua mới</span><strong>MUA / CHỜ</strong></div>
      <div class="commercial-premium-row"><span>Nắm giữ</span><strong>GIỮ / TĂNG / GIẢM / BÁN</strong></div>
      <div class="commercial-premium-row"><span>Kế hoạch</span><strong>Buy Zone · Stop · Target · Risk/Reward</strong></div>
      <div class="commercial-premium-row"><span>Theo dõi</span><strong>My StockRadar + Action Alert theo quyền gói</strong></div>
      <div class="commercial-premium-actions"><a class="button button-primary" href="dang-ky/?plan=premium">Premium · 199K/30 ngày</a><a class="button button-secondary" href="dang-nhap/">Đăng nhập</a></div>
    </div></div>'''
    source, count = re.subn(r'<div data-premium-gate-copy>.*?</div>\s*</aside>', preview + '\n</aside>', source, count=1, flags=re.I | re.S)
    if count != 1:
        raise RuntimeError("Premium stock gate copy not found")
    return source


def commercial_signup(source: str) -> str:
    source = add_body_class(source, "commercial-auth-page")
    source = remove_block(source, "auth-intro", tag="section", required=True)
    source = source.replace("Tạo tài khoản Free hoặc Premium — StockRadar", "Tạo tài khoản — StockRadar")
    source = source.replace("EMAIL + PASSWORD", "STOCKRADAR")
    source = source.replace("Nhập email và mật khẩu. Nếu chọn Premium, tạo tài khoản xong sẽ chuyển thẳng sang thanh toán 199.000đ/30 ngày.", "Email + mật khẩu.")
    source = source.replace("Gói bạn muốn đăng ký", "Chọn gói")
    source = source.replace("StockRadar AI 10 câu/ngày + Tra cứu, Radar và các nội dung công khai; không có email nội dung hằng ngày.", "AI 10 câu/ngày · Tra cứu · Radar.")
    source = source.replace("StockRadar AI không giới hạn + quyết định đầy đủ, My StockRadar, báo cáo 09:00 và Action Alert theo watchlist.", "AI không giới hạn · Quyết định · My StockRadar · Action Alert.")
    source = source.replace("Free có 10 câu StockRadar AI/ngày và chỉ nhận email hệ thống cần thiết. Email nội dung là quyền Premium.", "Free 10 câu AI/ngày · Premium không giới hạn.")
    source = source.replace("Tôi đã đọc và đồng ý với ", "Tôi đồng ý với ")
    source = source.replace("Tùy chọn email Premium", "Email Premium (tùy chọn)")
    source = source.replace(" — ưu tiên watchlist/mã đang sở hữu trước, bối cảnh thị trường sau.", "")
    source = source.replace(" — chỉ gửi khi trạng thái hành động của mã được theo dõi thay đổi đủ điều kiện; không đổi thì không tạo alert riêng.", "")
    source = source.replace("Premium mặc định bật Báo cáo StockRadar lúc 09:00 và Action Alert trong phiên. Người dùng có thể bỏ chọn nếu không muốn nhận một trong hai loại email.", "Có thể bật/tắt từng loại email.")
    source = source.replace("Mật khẩu không được đưa vào analytics hoặc dữ liệu thị trường.", "")
    source = source.replace("Bảo mật:</strong> StockRadar không yêu cầu OTP ngân hàng, OTP tài khoản chứng khoán hoặc mã giao dịch.", "Bảo mật:</strong> Không yêu cầu OTP ngân hàng hoặc tài khoản chứng khoán.")
    return source


def commercial_login(source: str) -> str:
    source = add_body_class(source, "commercial-auth-page")
    source = remove_block(source, "auth-intro", tag="section", required=True)
    source = source.replace("SECURE AUTH", "STOCKRADAR")
    source = source.replace("Nhập thông tin tài khoản StockRadar.", "Email + mật khẩu.")
    source = source.replace("Chưa có tài khoản? <a href=\"signup/\">Đăng ký miễn phí</a>", "Chưa có tài khoản? <a href=\"dang-ky/?plan=free\">Bắt đầu miễn phí</a>")
    return source


def commercial_checkout(source: str) -> str:
    source = add_body_class(source, "commercial-checkout-page")
    source = source.replace("Thanh toán một lần.<br>Kích hoạt đúng 30 ngày Premium.", "StockRadar Premium · 30 ngày")
    source = source.replace(
        "Giá 199.000đ/30 ngày. Không tự gia hạn. Tài khoản nhận tiền chính thức là VPBank · 0934389822 · NGUYỄN TỬ LINH. QR tài khoản hiển thị ngay; sau khi đăng nhập hệ thống tạo mã chuyển khoản riêng cho đúng tài khoản Premium.",
        "199.000đ · Không tự gia hạn · Thanh toán VietQR/VPBank.",
    )
    source = source.replace("Thông tin thanh toán StockRadar Premium", "Thanh toán Premium")
    source = source.replace(
        "Tài khoản nhận tiền chính thức: <strong>VPBank · 0934389822 · NGUYỄN TỬ LINH</strong>. QR hiển thị ngay để quét; hãy đăng nhập trước khi chuyển tiền để lấy đúng nội dung chuyển khoản SR riêng.",
        "Đăng nhập để nhận mã chuyển khoản SR riêng.",
    )
    source = source.replace(
        "<strong>Quan trọng:</strong> QR trên chuyển đúng tới VPBank 0934389822 và số tiền 199.000đ. Trước khi chuyển, đăng nhập để hệ thống cấp <strong>nội dung chuyển khoản SR riêng</strong>; nhập đúng mã SR đó để StockRadar đối soát chính xác.",
        "<strong>Lưu ý:</strong> dùng đúng nội dung chuyển khoản SR được cấp cho tài khoản của bạn.",
    )
    source = source.replace(
        "Bấm xác nhận để StockRadar gửi yêu cầu duyệt tới email quản trị. Sau khi tiền thực nhận được kiểm tra và xác nhận, tài khoản tự chuyển sang Premium, cộng đúng 30 ngày và gửi email kết quả cho khách hàng.",
        "Sau khi chuyển khoản, gửi xác nhận để kích hoạt Premium sau khi đối soát.",
    )
    source = source.replace("Lớp quyết định, kế hoạch giao dịch và cảnh báo hành động dành cho tài khoản trả phí.", "AI không giới hạn + lớp quyết định.")
    source = re.sub(
        r'<ul class="checkout-features">.*?</ul>',
        '<ul class="checkout-features"><li>AI không giới hạn</li><li>MUA/CHỜ · GIỮ/TĂNG/GIẢM/BÁN</li><li>Buy Zone · Stop · Target · Risk/Reward</li><li>My StockRadar + quyền cảnh báo theo gói</li></ul>',
        source,
        count=1,
        flags=re.I | re.S,
    )
    source = re.sub(
        r'<div class="checkout-notes">.*?</div>\s*</div>\s*</aside>',
        '<div class="checkout-notes"><div class="checkout-note"><span>✓</span><span><b>Kích hoạt:</b> sau khi thanh toán được xác minh.</span></div><div class="checkout-note"><span>✓</span><span><b>Hết hạn:</b> trở về Free, không xóa tài khoản.</span></div></div></div></aside>',
        source,
        count=1,
        flags=re.I | re.S,
    )
    source = remove_block(source, "checkout-help", tag="div", required=False)
    return source


def process(output: Path, route: str) -> None:
    path = output / route / "index.html"
    source = inject_style(read(path))
    transforms = {
        "co-phieu": commercial_stock,
        "signup": commercial_signup,
        "dang-nhap": commercial_login,
        "thanh-toan": commercial_checkout,
    }
    write(path, transforms[route](source))


def verify(output: Path) -> None:
    pages = {route: read(output / route / "index.html") for route in ROUTES}
    for route, source in pages.items():
        if STYLE_MARKER not in source:
            raise RuntimeError(f"Commercial v2 CSS missing from {route}")
    if "4M · Payback · CANSLIM" in pages["co-phieu"] or "premium-analysis-stack" in pages["co-phieu"]:
        raise RuntimeError("Stock page still exposes verbose methodology preview")
    if "auth-intro" in pages["signup"] or "auth-intro" in pages["dang-nhap"]:
        raise RuntimeError("Auth pages still contain marketing intro block")
    if "checkout-help" in pages["thanh-toan"]:
        raise RuntimeError("Checkout still contains duplicated help walkthrough")
    for marker in ("data-checkout-confirm", "data-checkout-reference", "0934389822", "VPBank"):
        if marker not in pages["thanh-toan"]:
            raise RuntimeError(f"Checkout functional marker missing: {marker}")
    for marker in ("data-auth-signup-form", "email_daily_brief", "email_event_alerts"):
        if marker not in pages["signup"]:
            raise RuntimeError(f"Signup functional marker missing: {marker}")
    print("Commercial surface v2: PASS (stock detail + auth + checkout compact and functional)")


def main() -> None:
    output = args().output.resolve()
    if not output.is_dir():
        raise RuntimeError(f"Pages output does not exist: {output}")
    if not (output / "assets" / STYLE_NAME).is_file():
        raise RuntimeError(f"Missing commercial v2 stylesheet: {STYLE_NAME}")
    for route in ROUTES:
        process(output, route)
    verify(output)


if __name__ == "__main__":
    main()
