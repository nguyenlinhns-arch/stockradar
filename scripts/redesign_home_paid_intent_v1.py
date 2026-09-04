#!/usr/bin/env python3
"""Rebuild the production homepage around the paid-intent buyer journey.

The public homepage should create the desire to pay by moving through:
lookup -> personal use case -> proof -> Premium price/CTA.
No fake ticker result, performance number, or payment capability is introduced here.
"""

from __future__ import annotations

import argparse
from pathlib import Path


SECTIONS = '''<section class="home-paid-intent-v1" data-home-paid-intent-v1 aria-labelledby="home-paid-intent-title">
      <div class="container">
        <header class="home-paid-intent-head">
          <span class="panel-label">SAU KHI TRA MÃ</span>
          <h2 id="home-paid-intent-title">Đừng tự canh từng mã. Hãy để StockRadar theo dõi việc cần làm.</h2>
          <p>Premium biến mỗi mã bạn quan tâm thành một trạng thái sống: mua mới được chưa, vị thế đang có nên làm gì, mốc nào cần bảo vệ và khi nào quyết định thay đổi.</p>
        </header>

        <div class="home-paid-intent-grid">
          <article class="home-paid-monitor" aria-label="Cấu trúc theo dõi một mã Premium">
            <div class="home-paid-monitor-top">
              <div><span>MÃ BẠN QUAN TÂM</span><strong data-home-intent-ticker>MÃ CỦA BẠN</strong></div>
              <em>PREMIUM THEO DÕI</em>
            </div>
            <div class="home-paid-monitor-rows">
              <div class="home-paid-monitor-row"><span>Nếu chưa có hàng</span><strong>MUA / CHỜ</strong></div>
              <div class="home-paid-monitor-row"><span>Nếu đang nắm giữ</span><strong>GIỮ / TĂNG / GIẢM / BÁN</strong></div>
              <div class="home-paid-monitor-row"><span>Mốc hành động</span><strong>Vùng mua · Stop · Target</strong></div>
              <div class="home-paid-monitor-row"><span>Khi trạng thái thay đổi</span><strong>CẢNH BÁO</strong></div>
            </div>
          </article>

          <aside class="home-paid-promise">
            <span class="panel-label">GIÁ TRỊ TRẢ PHÍ</span>
            <h3>Không phải đọc thêm. Là bớt việc phải tự theo dõi.</h3>
            <p>Free phù hợp khi bạn muốn tự tra cứu. Premium phù hợp khi bạn muốn StockRadar theo dõi đúng các mã của mình và chỉ báo khi có việc đáng chú ý.</p>
            <div class="home-paid-promise-list">
              <span>Tách quyết định mua mới khỏi quản trị vị thế đang có.</span>
              <span>Biết mốc nào làm quyết định hiện tại không còn đúng.</span>
              <span>Không đổi trạng thái thì không tạo cảnh báo hành động.</span>
            </div>
            <div class="home-paid-promise-actions">
              <a class="button button-primary" href="#home-proof-v1">Kiểm chứng trước khi mua</a>
              <a class="button button-secondary" href="#ticker-hero">Tra một mã trước</a>
            </div>
          </aside>
        </div>
      </div>
    </section>

    <section class="home-proof-v1" id="home-proof-v1" aria-labelledby="home-proof-title">
      <div class="container">
        <header class="home-proof-head">
          <span class="panel-label">KIỂM CHỨNG TRƯỚC KHI TRẢ TIỀN</span>
          <h2 id="home-proof-title">Đừng tin lời quảng cáo. Hãy xem lịch sử.</h2>
          <p>StockRadar phải cho bạn đủ dữ kiện để tự đánh giá chất lượng trước khi quyết định trả phí.</p>
        </header>
        <div class="home-proof-grid">
          <article class="home-proof-card"><b>Có dấu thời gian</b><span>Mỗi khuyến nghị và thay đổi trạng thái đều gắn thời điểm để biết quyết định được đưa ra khi nào.</span></article>
          <article class="home-proof-card"><b>Có cả lãi và lỗ</b><span>Không chỉ chọn lệnh đẹp. Kết quả đóng, lỗ và mức rủi ro phải được giữ lại để đối chiếu.</span></article>
          <article class="home-proof-card"><b>Không tính lệnh chưa kích hoạt</b><span>Không chạm vùng hành động thì không được tính như người dùng đã mua.</span></article>
          <article class="home-proof-card"><b>So cùng VN-Index</b><span>Kết quả cần được đặt cạnh benchmark trong cùng khoảng thời gian để tránh kết luận lệch.</span></article>
        </div>
        <div class="home-proof-actions">
          <a class="button button-primary" href="hieu-qua/" data-conversion-action="home_proof">Xem hiệu quả</a>
          <a class="button button-secondary" href="premium-mau/" data-conversion-action="home_premium_sample">Xem cấu trúc Premium</a>
        </div>
        <p class="home-proof-note">Chỉ số thực tế chỉ được hiển thị khi có dữ liệu đủ điều kiện công khai. Không đủ dữ kiện thì StockRadar không dựng số để thuyết phục mua.</p>
      </div>
    </section>

    <section class="home-premium-offer-v1" id="home-premium-offer" data-email-conversion aria-labelledby="home-premium-offer-title">
      <div class="container">
        <div class="home-premium-offer-card">
          <div class="home-premium-offer-copy">
            <span class="panel-label">PREMIUM · THEO DÕI MÃ CỦA TÔI</span>
            <h2 id="home-premium-offer-title">Để StockRadar theo dõi các mã bạn thực sự quan tâm.</h2>
            <p>Bạn trả tiền cho lớp quyết định và theo dõi thay đổi — không phải để nhận thêm một danh sách thông tin phải tự đọc.</p>
            <div class="home-premium-feature-grid">
              <div class="home-premium-feature"><strong>Mua mới</strong><span>MUA / CHỜ theo khung bạn chọn.</span></div>
              <div class="home-premium-feature"><strong>Vị thế đang có</strong><span>GIỮ / TĂNG / GIẢM / BÁN.</span></div>
              <div class="home-premium-feature"><strong>Quản trị rủi ro</strong><span>Vùng mua · Stop · Target · Risk/Reward.</span></div>
              <div class="home-premium-feature"><strong>Theo dõi thay đổi</strong><span>Ưu tiên watchlist của bạn và báo khi trạng thái đổi.</span></div>
            </div>
          </div>
          <aside class="home-premium-buybox">
            <span class="panel-label">STOCKRADAR PREMIUM</span>
            <div class="home-premium-price"><strong>199.000đ</strong><span>/ 30 ngày</span></div>
            <a class="button button-primary" href="signup/?plan=premium" data-premium-conversion-cta data-conversion-action="home_premium">Theo dõi mã của tôi</a>
            <a class="home-premium-secondary" href="dang-ky/">So sánh Free / Premium</a>
            <div class="home-premium-trust">
              <span>Không tự gia hạn.</span>
              <span>Không cần mật khẩu hoặc OTP tài khoản môi giới.</span>
              <span>Tạo tài khoản không tự phát sinh thu phí.</span>
              <span>Không cam kết lợi nhuận.</span>
            </div>
          </aside>
        </div>
      </div>
    </section>

    <section class="home-free-exit-v1" aria-label="Lựa chọn miễn phí">
      <div class="container home-free-exit-inner">
        <div><strong>Chưa cần Premium?</strong><span>Bắt đầu bằng một mã bạn đang quan tâm và tự đánh giá StockRadar trước.</span></div>
        <div class="home-free-exit-actions"><a class="button button-secondary" href="#ticker-hero">Tra mã miễn phí</a><a class="button button-secondary" href="nhan-ban-tin/">Xem bản rà soát Free</a></div>
      </div>
    </section>'''


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    return parser.parse_args()


def main() -> None:
    output = parse_args().output.resolve()
    home = output / "index.html"
    css = output / "assets" / "home-paid-intent-v1.css"
    js = output / "assets" / "home-paid-intent-v1.js"
    if not home.is_file():
        raise RuntimeError(f"Homepage missing: {home}")
    if not css.is_file() or not js.is_file():
        raise RuntimeError("Paid-intent homepage assets missing")

    source = home.read_text(encoding="utf-8")
    start = source.find('<section class="home-decision-v2"')
    end = source.find("</main>")
    if start < 0 or end < 0 or start >= end:
        raise RuntimeError("Could not locate homepage conversion body")

    source = source[:start] + SECTIONS + "\n  " + source[end:]

    source = source.replace(
        '<p class="stock-analysis-intro">Nhập mã HOSE để xem ngay <strong>MUA hay CHỜ</strong>. Khi cần quyết định đầy đủ, Premium mở trạng thái vị thế, vùng mua, Stop, Target và cảnh báo thay đổi.</p>',
        '<p class="stock-analysis-intro">Nhập mã HOSE bạn đang quan tâm. Xem bối cảnh miễn phí trước; nếu cần StockRadar theo dõi việc nên làm và báo khi quyết định thay đổi, Premium mở lớp đó.</p>',
        1,
    )

    source = source.replace(
        '<link rel="stylesheet" href="assets/home-decision-v2.css?v=20260904-decision2">\n',
        "",
        1,
    )
    mobile_start = source.find('<div class="mobile-newsletter-bar"')
    if mobile_start >= 0:
        mobile_end = source.find("</div>", mobile_start)
        if mobile_end >= 0:
            source = source[:mobile_start] + source[mobile_end + len("</div>"):]

    css_tag = '<link rel="stylesheet" href="assets/home-paid-intent-v1.css?v=20260904-paid1" data-home-paid-intent-v1>\n'
    js_tag = '<script src="assets/home-paid-intent-v1.js?v=20260904-paid1" defer></script>\n'
    if "home-paid-intent-v1.css" not in source:
        source = source.replace("</head>", css_tag + js_tag + "</head>", 1)

    home.write_text(source, encoding="utf-8")
    print("Homepage paid-intent v1: PASS (lookup → personal value → proof → Premium)")


if __name__ == "__main__":
    main()
