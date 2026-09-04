#!/usr/bin/env python3
"""Fail-close Premium checkout until the paid product is production-ready.

When STOCKRADAR_CHECKOUT_READY=0, the final Pages artifact contains a clear
Premium-paused page and no bank account, QR, transfer reference, or payment CTA.
When the gate is explicitly opened, the production receiving bank is exposed and
user-specific transfer reference/VietQR remain session-bound.
"""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

BANK_NAME = "VPBank"
ACCOUNT_NUMBER = "0934389822"
ACCOUNT_NAME = "NGUYỄN TỬ LINH"


def checkout_ready() -> bool:
    return os.environ.get("STOCKRADAR_CHECKOUT_READY", "").strip().lower() in {"1", "true", "yes", "on"}


def paused_page() -> str:
    return '''<!doctype html>
<html lang="vi" data-api-mode="disabled">
<head>
  <base href="../">
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="robots" content="noindex,nofollow">
  <meta name="description" content="StockRadar Premium đang tạm dừng kích hoạt tài khoản trả phí mới cho tới khi Decision Feed và email production hoàn tất kiểm thử end-to-end.">
  <title>Premium đang tạm dừng kích hoạt — StockRadar</title>
  <link rel="icon" href="assets/logo.svg">
  <link rel="stylesheet" href="assets/styles.css?v=20260904-checkout-paused1">
  <link rel="stylesheet" href="assets/checkout-v1.css?v=20260904-checkout-paused1">
</head>
<body data-proposition="checkout" data-checkout-ready="false">
  <a class="skip-link" href="#content">Bỏ qua điều hướng</a>
  <header class="site-header"><div class="container nav"><a class="brand" href="./" aria-label="Trang chủ StockRadar"><img src="assets/logo.svg" alt="StockRadar"></a><nav class="nav-links" aria-label="Điều hướng chính"><a href="./">AI StockRadar</a><a href="radar5/">Radar</a><a href="kiem-tra-co-phieu/">Tra cứu mã</a><a href="hieu-qua/">Hiệu quả</a></nav></div></header>
  <main id="content" class="checkout-shell">
    <section class="checkout-hero"><div class="checkout-hero-inner">
      <span class="checkout-eyebrow">STOCKRADAR PREMIUM · FAIL-CLOSED</span>
      <h1>Premium tạm dừng kích hoạt mới.</h1>
      <p>StockRadar chưa nhận thanh toán mới cho tới khi dữ liệu quyết định, AI, Action Alert và email production hoàn tất kiểm thử end-to-end. Tài khoản Free vẫn hoạt động bình thường.</p>
      <div class="checkout-steps" aria-label="Trạng thái Premium"><span class="checkout-step is-active"><b>1</b>Chuẩn hóa dữ liệu</span><span class="checkout-step"><b>2</b>Kiểm thử Paid E2E</span><span class="checkout-step"><b>3</b>Mở lại Premium</span></div>
    </div></section>
    <section class="checkout-main"><div class="checkout-grid">
      <article class="checkout-card">
        <header class="checkout-card-head"><span class="checkout-section-label">BẢO VỆ NGƯỜI DÙNG TRẢ PHÍ</span><h2>Chỉ thu tiền khi giá trị cốt lõi đã chạy thật.</h2><p>Decision Feed hiện chưa đạt publication gate. Vì vậy StockRadar khóa toàn bộ QR, số tài khoản, nội dung chuyển khoản và nút xác nhận thanh toán trên website.</p></header>
        <div class="checkout-help">
          <article><strong>Free vẫn dùng được</strong><span>StockRadar AI theo hạn mức Free, tra cứu mã, Radar công khai và watchlist cơ bản theo trạng thái dữ liệu hiện có.</span></article>
          <article><strong>Premium sẽ mở lại khi đạt chuẩn</strong><span>AI không giới hạn, lớp quyết định, Buy Zone · Stop · Target · R/R, Daily 09:00 và Action Alert trong phiên.</span></article>
          <article><strong>Không thu trước rồi chờ dữ liệu</strong><span>Việc tạm khóa checkout là chủ động để tránh người dùng trả phí nhưng chưa nhận đủ sản phẩm đã cam kết.</span></article>
        </div>
        <div class="hero-actions" style="margin-top:22px"><a class="button button-primary" href="signup/?plan=free">Tạo tài khoản Free</a><a class="button button-secondary" href="dang-ky/#premium">Xem quyền lợi Premium</a></div>
      </article>
      <aside class="checkout-card checkout-summary"><div class="checkout-summary-inner">
        <span class="checkout-plan-pill">PREMIUM</span><h2>199.000đ / 30 ngày</h2><p>Giá sẽ chỉ được thu khi cổng Premium được mở lại.</p>
        <ul class="checkout-features"><li>StockRadar AI không giới hạn.</li><li>Hai quyết định riêng: mua mới và đang nắm giữ.</li><li>Buy Zone · tỷ trọng · Stop-loss · Target · Upside/Downside · Risk/Reward.</li><li>Cảnh báo tại 10:30 · 11:15 · 13:30 · 14:15 khi trạng thái đủ điều kiện thay đổi.</li><li>Báo cáo email 09:00 và Action Alert khi delivery production đạt chuẩn.</li></ul>
        <div class="checkout-warning"><strong>Trạng thái:</strong> chưa nhận thanh toán mới. Không chuyển khoản thủ công ngoài luồng website.</div>
      </div></aside>
    </div></section>
  </main>
  <footer class="site-footer"><div class="container"><div class="footer-grid"><strong>STOCKRADAR.VN</strong><div class="footer-links"><a href="./">AI StockRadar</a><a href="dang-ky/">Free / Premium</a><a href="dieu-khoan/">Điều khoản</a><a href="quyen-rieng-tu/">Quyền riêng tư</a></div></div><p class="disclaimer">StockRadar chỉ mở thanh toán khi sản phẩm Paid đáp ứng đầy đủ các cổng dữ liệu, vận hành và delivery.</p></div></footer>
</body>
</html>'''


def expose_bank(source: str) -> str:
    source = re.sub(
        r'<p>Đăng nhập để hệ thống cấp số tiền, mã giao dịch và thời hạn thanh toán\. Không dùng lại nội dung chuyển khoản của giao dịch cũ\.</p>',
        '<p>Tài khoản nhận tiền chính thức của StockRadar là VPBank · 0934389822 · NGUYỄN TỬ LINH. Đăng nhập để hệ thống tạo nội dung chuyển khoản riêng, QR và thời hạn thanh toán cho đúng tài khoản.</p>',
        source,
        count=1,
    )
    source = source.replace(
        '<span>Đăng nhập và tạo yêu cầu thanh toán để hiển thị QR.</span>',
        '<span>Đăng nhập để hệ thống tạo QR kèm nội dung chuyển khoản riêng.</span>',
        1,
    )
    source = re.sub(
        r'(<strong\s+data-checkout-bank[^>]*>).*?(</strong>)',
        rf'\g<1>{BANK_NAME}\g<2>',
        source,
        count=1,
        flags=re.DOTALL,
    )
    source = re.sub(
        r'(<strong\s+data-checkout-account-number[^>]*>).*?(</strong>)',
        rf'\g<1>{ACCOUNT_NUMBER}\g<2>',
        source,
        count=1,
        flags=re.DOTALL,
    )
    source = re.sub(
        r'(<strong\s+data-checkout-account-name[^>]*>).*?(</strong>)',
        rf'\g<1>{ACCOUNT_NAME}\g<2>',
        source,
        count=1,
        flags=re.DOTALL,
    )
    source = re.sub(
        r'(<button\s+class="checkout-copy"\s+type="button"\s+data-copy-account)\s+data-copy-value="[^"]*"(?:\s+disabled)?',
        rf'\g<1> data-copy-value="{ACCOUNT_NUMBER}"',
        source,
        count=1,
    )

    required = (
        f'data-checkout-bank>{BANK_NAME}</strong>',
        f'data-checkout-account-number>{ACCOUNT_NUMBER}</strong>',
        f'data-checkout-account-name>{ACCOUNT_NAME}</strong>',
        f'data-copy-account data-copy-value="{ACCOUNT_NUMBER}"',
        'data-checkout-reference>—</strong>',
        'data-checkout-expiry>—</strong>',
        'Đăng nhập để hệ thống tạo QR kèm nội dung chuyển khoản riêng.',
    )
    for marker in required:
        if marker not in source:
            raise RuntimeError(f"Checkout public bank contract missing: {marker}")
    return source


def enforce(output: Path) -> Path:
    page = output / "thanh-toan" / "index.html"
    if not page.exists():
        raise FileNotFoundError(page)

    if not checkout_ready():
        page.write_text(paused_page(), encoding="utf-8")
        print(f"Premium checkout fail-closed: {page}")
        return page

    source = expose_bank(page.read_text(encoding="utf-8"))
    page.write_text(source, encoding="utf-8")
    print(f"Premium checkout opened with public bank info: {page}")
    return page


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    enforce(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
