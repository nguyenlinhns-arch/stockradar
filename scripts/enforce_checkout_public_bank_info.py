#!/usr/bin/env python3
"""Fail-close Premium checkout in the final Pages artifact.

The source checkout runtime may remain available for development and future
activation, but public Pages must not expose payment instructions until the
paid product has passed Decision Feed + email end-to-end readiness.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path


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
  <link rel="stylesheet" href="assets/styles.css?v=20260904-checkout-paused2">
  <link rel="stylesheet" href="assets/checkout-v1.css?v=20260904-checkout-paused2">
</head>
<body data-proposition="checkout" data-checkout-ready="false">
  <a class="skip-link" href="#content">Bỏ qua điều hướng</a>
  <header class="site-header"><div class="container nav"><a class="brand" href="./" aria-label="Trang chủ StockRadar"><img src="assets/logo.svg" alt="StockRadar"></a><nav class="nav-links" aria-label="Điều hướng chính"><a href="./">AI StockRadar</a><a href="radar5/">Radar</a><a href="kiem-tra-co-phieu/">Tra cứu mã</a><a href="hieu-qua/">Hiệu quả</a></nav></div></header>
  <main id="content" class="checkout-shell">
    <section class="checkout-hero"><div class="checkout-hero-inner">
      <span class="checkout-eyebrow">STOCKRADAR PREMIUM · FAIL-CLOSED</span>
      <h1>Premium tạm dừng kích hoạt mới.</h1>
      <p>StockRadar chưa nhận thanh toán Premium mới cho tới khi dữ liệu quyết định, AI, Action Alert và email production hoàn tất kiểm thử end-to-end. Tài khoản Free vẫn hoạt động bình thường.</p>
      <div class="checkout-steps" aria-label="Trạng thái Premium"><span class="checkout-step is-active"><b>1</b>Chuẩn hóa dữ liệu</span><span class="checkout-step"><b>2</b>Kiểm thử Paid E2E</span><span class="checkout-step"><b>3</b>Mở lại Premium</span></div>
    </div></section>
    <section class="checkout-main"><div class="checkout-grid">
      <article class="checkout-card">
        <header class="checkout-card-head"><span class="checkout-section-label">BẢO VỆ NGƯỜI DÙNG TRẢ PHÍ</span><h2>Chỉ thu tiền khi giá trị cốt lõi đã chạy thật.</h2><p>Decision Feed hiện chưa đạt publication gate. Vì vậy bản public khóa QR, thông tin chuyển khoản, mã giao dịch và nút xác nhận thanh toán.</p></header>
        <div class="checkout-help">
          <article><strong>Free vẫn dùng được</strong><span>StockRadar AI theo hạn mức Free, tra cứu mã, Radar công khai và watchlist cơ bản theo trạng thái dữ liệu hiện có.</span></article>
          <article><strong>Premium sẽ mở lại khi đạt chuẩn</strong><span>AI không giới hạn, lớp quyết định, Buy Zone · Stop · Target · R/R, Daily 09:00 và Action Alert trong phiên.</span></article>
          <article><strong>Không thu trước rồi chờ dữ liệu</strong><span>Checkout được khóa chủ động để người dùng không trả phí trước khi sản phẩm Paid đáp ứng đủ cam kết.</span></article>
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


def enforce(output: Path) -> Path:
    page = output / "thanh-toan" / "index.html"
    if not page.exists():
        raise FileNotFoundError(page)

    if not checkout_ready():
        page.write_text(paused_page(), encoding="utf-8")
        print(f"Premium checkout fail-closed: {page}")
        return page

    source = page.read_text(encoding="utf-8")
    if 'data-checkout-ready="false"' in source or "Premium tạm dừng kích hoạt mới" in source:
        raise RuntimeError("Checkout-open build received a stale paused source page")
    print(f"Premium checkout gate open; preserving authenticated source surface: {page}")
    return page


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    enforce(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
