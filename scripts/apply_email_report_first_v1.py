#!/usr/bin/env python3
"""Final production homepage switch: email/report-first, no homepage AI chat.

This transform intentionally runs after every legacy/commercial/workspace pass so older
AI-first build steps cannot overwrite the production homepage. It does not enable email
delivery or billing; runtime readiness remains the source of truth.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

STYLE_NAME = "email-report-first-v1.css"
STYLE_MARKER = "data-email-report-first"

TITLE = "StockRadar — Báo cáo & cảnh báo email cổ phiếu HOSE"
DESCRIPTION = (
    "StockRadar tập trung vào báo cáo cổ phiếu HOSE qua email: bản tin 09:00, "
    "cảnh báo điểm mua/bán trong phiên, Buy Zone, Stop-loss, Target và Risk/Reward."
)

NAV = """<nav class="nav-links" id="site-menu" aria-label="Điều hướng chính" data-nav-menu>
        <a href="#bao-cao-email" aria-current="page">Báo cáo email</a>
        <a href="hom-nay/">Hôm nay</a>
        <a href="radar5/">Radar HOSE</a>
        <a href="khuyen-nghi/">Khuyến nghị</a>
        <a href="hieu-qua/">Hiệu quả</a>
        <a href="tai-khoan/">Tài khoản</a>
      </nav>"""

FOOTER_LINKS = """<div class="footer-links">
        <a href="#bao-cao-email">Báo cáo email</a>
        <a href="radar5/">Radar</a>
        <a href="khuyen-nghi/">Khuyến nghị</a>
        <a href="hieu-qua/">Hiệu quả</a>
        <a href="dieu-khoan/">Điều khoản</a>
        <a href="quyen-rieng-tu/">Quyền riêng tư</a>
      </div>"""

MAIN = r"""<main id="content" class="email-report-shell" data-email-report-first>
  <section class="report-hero" id="bao-cao-email">
    <div class="container report-hero-grid">
      <div class="report-hero-copy">
        <span class="report-kicker">STOCKRADAR · EMAIL REPORT</span>
        <h1>Báo cáo cổ phiếu HOSE gửi thẳng vào email.</h1>
        <p class="report-lead">Bản tin <strong>09:00 mỗi ngày giao dịch</strong> để chuẩn bị trước phiên. Trong phiên, StockRadar chỉ tạo cảnh báo khi xuất hiện thay đổi hành động đủ điều kiện tại 10:30 · 11:15 · 13:30 · 14:15.</p>
        <div class="report-actions">
          <a class="button button-primary" href="dang-ky/?plan=premium">Đăng ký nhận báo cáo</a>
          <a class="button button-secondary" href="khuyen-nghi/">Xem khuyến nghị đã công bố</a>
        </div>
        <div class="report-trust">
          <span>Chỉ HOSE</span>
          <span>Không gửi khi không có hành động</span>
          <span>Có ngày · giờ · mức giá</span>
        </div>
        <div class="delivery-line">
          <span>Trạng thái gửi Premium</span>
          <strong data-reco-email-state>Đang kiểm tra</strong>
          <small>Chỉ mở gửi tự động khi cổng dữ liệu và email đạt điều kiện vận hành.</small>
        </div>
      </div>

      <aside class="report-preview" aria-label="Mẫu báo cáo StockRadar">
        <div class="preview-head"><span>BẢN TIN 09:00</span><strong>StockRadar Daily</strong></div>
        <div class="preview-row"><span>Thị trường</span><b>VN-Index · VN30 · ngành · breadth</b></div>
        <div class="preview-row"><span>Cơ hội</span><b>Top 5 HOSE + Top 5 theo ngành</b></div>
        <div class="preview-row"><span>Kế hoạch</span><b>Buy Zone · Stop · Target · R/R</b></div>
        <div class="preview-row"><span>Khung thời gian</span><b>Ngắn hạn · 3–6 tháng · 12 tháng</b></div>
        <div class="preview-foot">Mỗi báo cáo ghi rõ ngày dữ liệu và thời điểm rà soát.</div>
      </aside>
    </div>
  </section>

  <section class="report-status">
    <div class="container report-status-grid" aria-label="Trạng thái dữ liệu">
      <div><span>Dữ liệu HOSE</span><strong data-market-status>Đang kiểm tra cập nhật</strong></div>
      <div><span>Cập nhật</span><strong data-market-updated>Đang tải…</strong></div>
      <div><span>Rà soát gần nhất</span><strong data-market-reviewed>Chưa xác minh</strong></div>
      <div><span>Phạm vi</span><strong data-market-coverage>HOSE</strong></div>
    </div>
  </section>

  <section class="report-section" aria-labelledby="email-products-title">
    <div class="container">
      <div class="report-section-head">
        <span>2 LỚP EMAIL</span>
        <h2 id="email-products-title">Một bản chuẩn bị trước phiên. Một lớp cảnh báo khi cần hành động.</h2>
      </div>
      <div class="email-product-grid">
        <article class="email-product-card">
          <span class="card-tag">09:00 · DAILY REPORT</span>
          <h3>Báo cáo phân tích hằng ngày</h3>
          <p>Tổng hợp thị trường, ngành mạnh/yếu, Top 5 cổ phiếu và Top 5 theo ngành; ưu tiên setup sớm, định giá và Risk/Reward.</p>
          <ul><li>Ngày dữ liệu ghi rõ trong tiêu đề</li><li>4M/Payback · CANSLIM · định giá · Stage/VCP/VPA</li><li>Bear · Base · Bull và điều kiện vô hiệu</li></ul>
        </article>
        <article class="email-product-card accent">
          <span class="card-tag">TRONG PHIÊN · ACTION ALERT</span>
          <h3>Chỉ gửi khi có hành động</h3>
          <p>Pocket Pivot, Early Breakout, Confirmed Breakout, nhồi lệnh, hạ tỷ trọng hoặc cắt lỗ/bán.</p>
          <ul><li>Giá · setup · Volume/RVOL</li><li>Buy Zone · tỷ trọng · Stop-loss</li><li>Target gần · 3–6 tháng · Upside/Downside · R/R</li></ul>
        </article>
      </div>
    </div>
  </section>

  <section class="report-section muted" data-live-radar-home aria-labelledby="latest-signals-title">
    <div class="container">
      <div class="report-section-head inline">
        <div><span>TÍN HIỆU ĐÃ ĐƯỢC PHÉP PHÁT HÀNH</span><h2 id="latest-signals-title">Khuyến nghị mới nhất</h2></div>
        <a href="khuyen-nghi/">Xem toàn bộ →</a>
      </div>
      <div class="reco-shell report-reco-shell">
        <div class="home-live-signals" data-home-live-signals hidden></div>
        <div class="reco-table-wrap" data-home-reco-table hidden>
          <table class="reco-table">
            <thead><tr><th>Mã</th><th>Trạng thái</th><th>Giá</th><th>Vùng mua</th><th>Cắt lỗ</th><th>Mục tiêu</th><th>R/R</th><th>Xác nhận</th><th>Email</th></tr></thead>
            <tbody data-home-reco-body></tbody>
          </table>
        </div>
        <div class="reco-empty" data-home-reco-empty>
          <strong>Đang kiểm tra tín hiệu đủ điều kiện.</strong>
          <span data-home-reco-reason>Không tạo khuyến nghị để lấp chỗ trống.</span>
        </div>
        <div class="reco-schedule">
          <div><span>Ngày dữ liệu</span><strong data-reco-price-date>—</strong></div>
          <div><span>Rà soát gần nhất</span><strong data-reco-reviewed-at>—</strong></div>
          <div><span>Rà soát tiếp</span><strong data-reco-next-review>—</strong></div>
          <div><span>Email Premium</span><strong data-reco-email-state>Đang kiểm tra</strong></div>
        </div>
      </div>
    </div>
  </section>

  <section class="report-section" aria-labelledby="report-content-title">
    <div class="container">
      <div class="report-section-head">
        <span>NỘI DUNG EMAIL</span>
        <h2 id="report-content-title">Nhìn vào email là biết cần làm gì và rủi ro ở đâu.</h2>
      </div>
      <div class="report-fields">
        <div><b>01</b><span>Mã · thời gian · giá · setup</span></div>
        <div><b>02</b><span>Volume/RVOL · VPA · Stage</span></div>
        <div><b>03</b><span>Buy Zone · tỷ trọng · Stop-loss</span></div>
        <div><b>04</b><span>Target gần · 3–6 tháng · 12 tháng</span></div>
        <div><b>05</b><span>Upside · Downside · Risk/Reward</span></div>
        <div><b>06</b><span>Thời gian kỳ vọng · điều kiện phá vỡ luận điểm</span></div>
      </div>
    </div>
  </section>

  <section class="report-section premium-band" aria-labelledby="plans-title">
    <div class="container premium-grid">
      <div>
        <span class="report-kicker">FREE / PREMIUM</span>
        <h2 id="plans-title">Free để theo dõi. Premium để nhận phân tích và cảnh báo qua email.</h2>
        <p>Free chỉ nhận email hệ thống cần thiết. Nội dung phân tích 09:00 và Action Alert thuộc lớp Premium khi cổng gửi được mở.</p>
      </div>
      <div class="premium-actions">
        <a class="button button-primary" href="dang-ky/?plan=premium">Đăng ký Premium</a>
        <a class="button button-secondary" href="tai-khoan/#email-preferences-title">Cài đặt email</a>
        <a class="text-link" href="hieu-qua/">Xem lịch sử hiệu quả →</a>
      </div>
    </div>
  </section>
</main>"""

CSS = r"""
body.email-report-home{background:#f5f7fb}
.email-report-shell{color:#10233f}
.report-hero{padding:54px 0 34px;background:linear-gradient(135deg,#071a34 0%,#0e2f58 100%);color:#fff}
.report-hero-grid{display:grid;grid-template-columns:minmax(0,1.35fr) minmax(320px,.65fr);gap:34px;align-items:center}
.report-kicker,.report-section-head>span,.card-tag{display:block;font-size:11px;font-weight:900;letter-spacing:.12em;text-transform:uppercase;color:#5ea7ff}
.report-hero h1{max-width:760px;margin:10px 0 14px;font-size:clamp(36px,6vw,66px);line-height:1.03;letter-spacing:-.045em;color:#fff}
.report-lead{max-width:760px;margin:0;color:#d8e6f7;font-size:17px;line-height:1.65}
.report-actions{display:flex;flex-wrap:wrap;gap:12px;margin-top:24px}
.report-hero .button-secondary{border-color:rgba(255,255,255,.35);color:#fff;background:transparent}
.report-trust{display:flex;flex-wrap:wrap;gap:9px;margin-top:20px}
.report-trust span{padding:7px 10px;border:1px solid rgba(255,255,255,.2);border-radius:999px;color:#c8d9ee;font-size:11px;font-weight:800}
.delivery-line{margin-top:20px;padding:13px 15px;border-left:3px solid #f1b94c;background:rgba(255,255,255,.07);display:grid;grid-template-columns:auto auto;gap:4px 12px;align-items:center}
.delivery-line span{font-size:11px;color:#c8d9ee}.delivery-line strong{justify-self:start;color:#fff}.delivery-line small{grid-column:1/-1;color:#b5c8df}
.report-preview{padding:22px;border:1px solid rgba(255,255,255,.18);background:rgba(255,255,255,.07);box-shadow:0 22px 55px rgba(0,0,0,.18)}
.preview-head{display:flex;justify-content:space-between;gap:16px;padding-bottom:14px;border-bottom:1px solid rgba(255,255,255,.16)}
.preview-head span{font-size:10px;font-weight:900;letter-spacing:.1em;color:#7bb7ff}.preview-head strong{font-size:16px}
.preview-row{display:grid;grid-template-columns:105px 1fr;gap:12px;padding:14px 0;border-bottom:1px solid rgba(255,255,255,.12)}
.preview-row span{font-size:11px;color:#a9c0da}.preview-row b{font-size:12px;color:#fff}.preview-foot{padding-top:14px;color:#b9cce2;font-size:11px;line-height:1.5}
.report-status{background:#fff;border-bottom:1px solid #dfe6ef}
.report-status-grid{display:grid;grid-template-columns:repeat(4,1fr)}
.report-status-grid>div{min-height:78px;padding:17px 18px;border-right:1px solid #e5eaf1}
.report-status-grid>div:last-child{border-right:0}.report-status-grid span{display:block;color:#748399;font-size:10px;font-weight:800;text-transform:uppercase}.report-status-grid strong{display:block;margin-top:7px;color:#10233f;font-size:12px}
.report-section{padding:52px 0}.report-section.muted{background:#eef3f8}.report-section-head{max-width:820px;margin-bottom:22px}.report-section-head h2{margin:7px 0 0;color:#10233f;font-size:clamp(27px,4vw,42px);line-height:1.08;letter-spacing:-.03em}
.report-section-head.inline{max-width:none;display:flex;justify-content:space-between;gap:20px;align-items:end}.report-section-head.inline a{font-weight:800}
.email-product-grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}.email-product-card{padding:25px;background:#fff;border:1px solid #dfe6ef;box-shadow:0 12px 32px rgba(17,39,68,.06)}.email-product-card.accent{border-top:4px solid #2373d4}.email-product-card h3{margin:8px 0 10px;color:#10233f;font-size:22px}.email-product-card p{color:#5f6f84;line-height:1.55}.email-product-card ul{margin:15px 0 0;padding-left:18px;color:#34465f}.email-product-card li{margin:8px 0}
.report-reco-shell{background:#fff}
.report-fields{display:grid;grid-template-columns:repeat(3,1fr);border:1px solid #dfe6ef;background:#fff}.report-fields>div{min-height:104px;padding:20px;border-right:1px solid #e5eaf1;border-bottom:1px solid #e5eaf1}.report-fields>div:nth-child(3n){border-right:0}.report-fields b{display:block;color:#2373d4;font-size:11px}.report-fields span{display:block;margin-top:11px;color:#253a55;font-size:13px;font-weight:800;line-height:1.45}
.premium-band{background:#0b203b;color:#fff}.premium-grid{display:grid;grid-template-columns:1fr auto;gap:34px;align-items:center}.premium-band h2{margin:8px 0 10px;color:#fff;font-size:clamp(28px,4vw,43px);line-height:1.08}.premium-band p{max-width:720px;color:#c0d2e6;line-height:1.55}.premium-actions{min-width:245px;display:grid;gap:10px}.premium-band .button-secondary{border-color:#46627f;color:#fff;background:transparent}.premium-band .text-link{color:#8fc1ff;font-size:12px;font-weight:800;text-align:center}
@media(max-width:900px){.report-hero-grid,.premium-grid{grid-template-columns:1fr}.report-status-grid{grid-template-columns:1fr 1fr}.email-product-grid{grid-template-columns:1fr}.report-fields{grid-template-columns:1fr 1fr}.report-fields>div:nth-child(3n){border-right:1px solid #e5eaf1}.report-fields>div:nth-child(2n){border-right:0}.premium-actions{min-width:0}}
@media(max-width:620px){.report-hero{padding-top:34px}.report-hero h1{font-size:40px}.report-status-grid{grid-template-columns:1fr}.report-status-grid>div{border-right:0}.report-section{padding:38px 0}.report-section-head.inline{align-items:flex-start;flex-direction:column}.report-fields{grid-template-columns:1fr}.report-fields>div{border-right:0!important}.delivery-line{grid-template-columns:1fr}.delivery-line small{grid-column:auto}.preview-row{grid-template-columns:1fr;gap:5px}}
"""

def replace_meta(source: str, name: str, content: str) -> str:
    pattern = re.compile(
        rf'<meta\s+name=["\']{re.escape(name)}["\']\s+content=["\'][^"\']*["\']\s*/?>',
        flags=re.I,
    )
    tag = f'<meta name="{name}" content="{content}">'
    source, count = pattern.subn(tag, source, count=1)
    if count == 0 and "</head>" in source:
        source = source.replace("</head>", tag + "\n</head>", 1)
    return source

def replace_property(source: str, prop: str, content: str) -> str:
    pattern = re.compile(
        rf'<meta\s+property=["\']{re.escape(prop)}["\']\s+content=["\'][^"\']*["\']\s*/?>',
        flags=re.I,
    )
    tag = f'<meta property="{prop}" content="{content}">'
    source, count = pattern.subn(tag, source, count=1)
    if count == 0 and "</head>" in source:
        source = source.replace("</head>", tag + "\n</head>", 1)
    return source

def remove_asset(source: str, filename: str) -> str:
    source = re.sub(
        rf'\s*<link\b[^>]*href=["\'][^"\']*assets/{re.escape(filename)}(?:\?[^"\']*)?["\'][^>]*>\s*',
        "\n",
        source,
        flags=re.I,
    )
    source = re.sub(
        rf'\s*<script\b[^>]*src=["\'][^"\']*assets/{re.escape(filename)}(?:\?[^"\']*)?["\'][^>]*>\s*</script>\s*',
        "\n",
        source,
        flags=re.I | re.S,
    )
    return source

def transform(output: Path) -> None:
    page = output / "index.html"
    if not page.is_file():
        raise RuntimeError(f"Homepage missing: {page}")

    assets = output / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    (assets / STYLE_NAME).write_text(CSS.strip() + "\n", encoding="utf-8")

    source = page.read_text(encoding="utf-8")

    source = re.sub(r"<title>.*?</title>", f"<title>{TITLE}</title>", source, count=1, flags=re.I | re.S)
    source = replace_meta(source, "description", DESCRIPTION)
    source = replace_property(source, "og:title", TITLE)
    source = replace_property(source, "og:description", DESCRIPTION)

    for filename in (
        "home-ai-center-v1.css",
        "ai-conversation-v2.css",
        "chatgpt-workspace.css",
        "project-channel.css",
        "ai-center.js",
        "chatgpt-workspace.js",
        "project-channel.js",
        "execution-config.js",
    ):
        source = remove_asset(source, filename)

    source = re.sub(
        r'<link\b[^>]*\bdata-email-report-first\b[^>]*>\s*',
        "",
        source,
        flags=re.I,
    )
    style_tag = f'<link rel="stylesheet" href="assets/{STYLE_NAME}?v=20260918-report1" {STYLE_MARKER}>'
    if "</head>" not in source:
        raise RuntimeError("Homepage missing </head>")
    source = source.replace("</head>", style_tag + "\n</head>", 1)

    source = re.sub(
        r'<body\b([^>]*)>',
        lambda m: _body(m.group(1)),
        source,
        count=1,
        flags=re.I,
    )

    source, nav_count = re.subn(
        r'<nav\b[^>]*class=["\'][^"\']*\bnav-links\b[^"\']*["\'][^>]*>.*?</nav>',
        NAV,
        source,
        count=1,
        flags=re.I | re.S,
    )
    if nav_count != 1:
        raise RuntimeError(f"Expected one primary nav, found {nav_count}")

    source, main_count = re.subn(
        r'<main\b[^>]*>.*?</main>',
        MAIN,
        source,
        count=1,
        flags=re.I | re.S,
    )
    if main_count != 1:
        raise RuntimeError(f"Expected one homepage main, found {main_count}")

    source, footer_count = re.subn(
        r'<div\b[^>]*class=["\'][^"\']*\bfooter-links\b[^"\']*["\'][^>]*>.*?</div>',
        FOOTER_LINKS,
        source,
        count=1,
        flags=re.I | re.S,
    )
    if footer_count != 1:
        raise RuntimeError(f"Expected one footer links block, found {footer_count}")

    source = source.replace(
        "StockRadar là công cụ hỗ trợ nghiên cứu và quản trị quyết định; không cam kết lợi nhuận và không tự đặt lệnh giao dịch.",
        "StockRadar cung cấp báo cáo nghiên cứu và cảnh báo theo dữ liệu đủ điều kiện; không cam kết lợi nhuận và không tự đặt lệnh giao dịch.",
    )

    page.write_text(source, encoding="utf-8")
    verify(page)

def _body(attrs: str) -> str:
    attrs = re.sub(r'\sdata-proposition=["\'][^"\']*["\']', "", attrs, flags=re.I)
    class_match = re.search(r'class=["\']([^"\']*)["\']', attrs, flags=re.I)
    if class_match:
        classes = [c for c in class_match.group(1).split() if c not in {"ai-home", "chatgpt-workspace-home"}]
        if "email-report-home" not in classes:
            classes.append("email-report-home")
        attrs = re.sub(
            r'class=["\'][^"\']*["\']',
            f'class="{" ".join(classes)}"',
            attrs,
            count=1,
            flags=re.I,
        )
    else:
        attrs += ' class="email-report-home"'
    return f'<body{attrs} data-proposition="email-report-first">'

def verify(page: Path) -> None:
    source = page.read_text(encoding="utf-8")
    required = (
        "data-email-report-first",
        "Báo cáo cổ phiếu HOSE gửi thẳng vào email.",
        "09:00",
        "10:30 · 11:15 · 13:30 · 14:15",
        "data-home-reco-body",
        "data-reco-email-state",
        f"assets/{STYLE_NAME}",
    )
    for marker in required:
        if marker not in source:
            raise RuntimeError(f"Email/report-first marker missing: {marker}")

    forbidden = (
        "data-stockradar-ai-center",
        "assets/chatgpt-workspace.js",
        "assets/project-channel.js",
        "assets/ai-center.js",
        ">StockRadar AI<",
        "Hỏi AI về một cổ phiếu",
    )
    for marker in forbidden:
        if marker in source:
            raise RuntimeError(f"Homepage AI marker survived: {marker}")

    if len(re.findall(r"<h1\b", source, flags=re.I)) != 1:
        raise RuntimeError("Homepage must contain exactly one h1")
    print("Email/report-first homepage: PASS (AI chat removed from home; report/email product is primary).")

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    transform(args.output.resolve())

if __name__ == "__main__":
    main()
