#!/usr/bin/env python3
"""Final StockRadar Pages hardening for strict AI-only research mode.

Compatibility entry point retained because pages.yml already invokes this file last.
The final artifact must not publish actionable recommendations, raw/downloadable stock
files, or public stock-data API surfaces. Email delivery is not enabled here.
"""
from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

STYLE_NAME = "ai-only-home-v2.css"
TITLE = "StockRadar — Nghiên cứu AI cổ phiếu HOSE"
DESCRIPTION = (
    "StockRadar vận hành ở chế độ AI-only research: tổng hợp nghiên cứu cổ phiếu HOSE "
    "theo dữ liệu đã kiểm tra, không phát hành khuyến nghị giao dịch hoặc dữ liệu thô công khai."
)

LOCKED_ROUTES = (
    "khuyen-nghi",
    "hieu-qua",
    "radar5",
    "hom-nay",
    "track-record",
    "breakout",
    "co-phieu",
    "kiem-tra-co-phieu",
    "risk",
    "thay-doi-hom-nay",
    "theo-doi",
    "premium-mau",
)

NAV = """<nav class="nav-links" id="site-menu" aria-label="Điều hướng chính" data-nav-menu>
        <a href="#ai-only-research" aria-current="page">Nghiên cứu AI</a>
        <a href="bao-cao-chatgpt/">Báo cáo AI</a>
        <a href="tai-khoan/">Tài khoản</a>
        <a href="dieu-khoan/">Điều khoản</a>
        <a href="quyen-rieng-tu/">Quyền riêng tư</a>
      </nav>"""

FOOTER_LINKS = """<div class="footer-links">
        <a href="#ai-only-research">Nghiên cứu AI</a>
        <a href="bao-cao-chatgpt/">Báo cáo AI</a>
        <a href="dieu-khoan/">Điều khoản</a>
        <a href="quyen-rieng-tu/">Quyền riêng tư</a>
      </div>"""

MAIN = r"""<main id="content" class="ai-only-shell" data-ai-only-home>
  <section class="ai-only-hero" id="ai-only-research">
    <div class="container ai-only-grid">
      <div>
        <span class="ai-only-kicker">STOCKRADAR · AI-ONLY RESEARCH</span>
        <h1>Nghiên cứu AI cổ phiếu HOSE.</h1>
        <p class="ai-only-lead">StockRadar hiện tập trung vào tổng hợp nghiên cứu mô tả, kiểm tra dữ liệu và lưu báo cáo phục vụ phân tích. <strong>Không phải khuyến nghị giao dịch.</strong></p>
        <div class="ai-only-actions">
          <a class="button button-primary" href="bao-cao-chatgpt/">Mở khu vực báo cáo AI</a>
          <a class="button button-secondary" href="dieu-khoan/">Xem nguyên tắc sử dụng</a>
        </div>
      </div>
      <aside class="ai-only-card" aria-label="Ranh giới vận hành StockRadar">
        <strong>Ranh giới vận hành hiện tại</strong>
        <ul>
          <li>Tổng hợp nghiên cứu AI: đang hoạt động</li>
          <li>Email tự động và cảnh báo giao dịch: tắt</li>
          <li>API dữ liệu cổ phiếu công khai: tắt</li>
          <li>Tải xuống hoặc phân phối lại dữ liệu thô: tắt</li>
        </ul>
      </aside>
    </div>
  </section>
  <section class="ai-only-status" aria-label="Trạng thái sản phẩm">
    <div class="container ai-only-status-grid">
      <div><span>Chế độ</span><strong>AI-only research</strong></div>
      <div><span>Email tự động</span><strong>Tắt</strong></div>
      <div><span>API dữ liệu công khai</span><strong>Tắt</strong></div>
      <div><span>Dữ liệu thô tải xuống</span><strong>Tắt</strong></div>
    </div>
  </section>
  <section class="ai-only-section">
    <div class="container">
      <div class="ai-only-heading"><span>NGUYÊN TẮC NGHIÊN CỨU</span><h2>Ưu tiên chất lượng dữ liệu và fail-closed.</h2></div>
      <div class="ai-only-cards">
        <article><h3>Tổng hợp có kiểm soát</h3><p>Kết hợp thông tin thị trường, doanh nghiệp và phương pháp nghiên cứu để mô tả bối cảnh; không chuyển thành chỉ dẫn mua, bán hoặc phân bổ danh mục.</p></article>
        <article><h3>Cách ly dữ liệu nghi nhiễm</h3><p>Ticker hoặc nguồn có dấu hiệu lẫn chéo, thiếu độ mới hay thiếu bằng chứng sẽ bị loại khỏi phần nghiên cứu sử dụng được cho tới khi được xác minh lại.</p></article>
        <article><h3>Không xuất bản dữ liệu thô</h3><p>Không mở tải xuống dữ liệu thị trường, không phân phối lại dữ liệu nguồn và không mở API dữ liệu cổ phiếu công khai trong chế độ hiện tại.</p></article>
      </div>
    </div>
  </section>
  <section class="ai-only-section muted">
    <div class="container ai-only-copy">
      <span class="ai-only-kicker">BÁO CÁO AI</span>
      <h2>Nghiên cứu mô tả, không hành động giao dịch.</h2>
      <p>Các báo cáo AI có thể trình bày xu hướng, chất lượng dữ liệu, bối cảnh ngành, yếu tố cơ bản, kỹ thuật và rủi ro ở mức nghiên cứu. Chúng không phát hành lệnh, vùng vào lệnh, mức dừng lỗ, mục tiêu giá, tỷ trọng vị thế hoặc chỉ dẫn thời điểm giao dịch.</p>
      <a class="button button-primary" href="bao-cao-chatgpt/">Xem khu vực báo cáo AI</a>
    </div>
  </section>
</main>"""

CSS = r"""
body.ai-only-home{background:#f5f7fb;color:#10233f}.ai-only-hero{padding:58px 0 44px;background:linear-gradient(135deg,#071a34 0%,#0e2f58 100%);color:#fff}.ai-only-grid{display:grid;grid-template-columns:minmax(0,1.35fr) minmax(300px,.65fr);gap:32px;align-items:center}.ai-only-kicker,.ai-only-heading>span{display:block;font-size:11px;font-weight:900;letter-spacing:.12em;text-transform:uppercase;color:#6eb2ff}.ai-only-hero h1{max-width:760px;margin:10px 0 14px;font-size:clamp(38px,6vw,66px);line-height:1.03;letter-spacing:-.045em;color:#fff}.ai-only-lead{max-width:760px;margin:0;color:#d8e6f7;font-size:17px;line-height:1.65}.ai-only-actions{display:flex;flex-wrap:wrap;gap:12px;margin-top:24px}.ai-only-hero .button-secondary{border-color:rgba(255,255,255,.35);color:#fff;background:transparent}.ai-only-card{padding:24px;border:1px solid rgba(255,255,255,.18);background:rgba(255,255,255,.07);box-shadow:0 22px 55px rgba(0,0,0,.18)}.ai-only-card strong{display:block;font-size:18px}.ai-only-card ul{margin:16px 0 0;padding-left:20px;color:#d6e5f5;line-height:1.75}.ai-only-status{background:#fff;border-bottom:1px solid #dfe6ef}.ai-only-status-grid{display:grid;grid-template-columns:repeat(4,1fr)}.ai-only-status-grid>div{min-height:78px;padding:17px 18px;border-right:1px solid #e5eaf1}.ai-only-status-grid span{display:block;color:#748399;font-size:10px;font-weight:800;text-transform:uppercase}.ai-only-status-grid strong{display:block;margin-top:7px;color:#10233f;font-size:13px}.ai-only-section{padding:54px 0}.ai-only-section.muted{background:#eef3f8}.ai-only-heading{max-width:820px;margin-bottom:22px}.ai-only-heading h2,.ai-only-copy h2{margin:7px 0 0;color:#10233f;font-size:clamp(28px,4vw,42px);line-height:1.08;letter-spacing:-.03em}.ai-only-cards{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}.ai-only-cards article{padding:24px;background:#fff;border:1px solid #dfe6ef;box-shadow:0 12px 32px rgba(17,39,68,.06)}.ai-only-cards h3{margin:0 0 10px;font-size:20px}.ai-only-cards p,.ai-only-copy p{color:#52647a;line-height:1.65}.ai-only-copy{max-width:900px}.ai-only-copy .button{margin-top:14px}@media(max-width:900px){.ai-only-grid,.ai-only-cards{grid-template-columns:1fr}.ai-only-status-grid{grid-template-columns:1fr 1fr}}@media(max-width:620px){.ai-only-hero{padding-top:36px}.ai-only-hero h1{font-size:40px}.ai-only-status-grid{grid-template-columns:1fr}.ai-only-status-grid>div{border-right:0}.ai-only-section{padding:40px 0}}
"""

LOCK_PAGE = """<!doctype html><html lang="vi" data-api-mode="disabled"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>StockRadar — AI-only research</title></head><body><main style="max-width:760px;margin:64px auto;padding:0 20px;font-family:Arial,sans-serif;color:#10233f"><h1>Nội dung này đang tạm khóa.</h1><p>StockRadar hiện vận hành ở chế độ AI-only research. Trang công khai chứa dữ liệu cổ phiếu, lịch sử khuyến nghị hoặc tín hiệu hành động không được phát hành trong chế độ này.</p><p><a href="../">Về trang chính</a> · <a href="../dieu-khoan/">Điều khoản</a></p></main></body></html>"""


def replace_meta(source: str, name: str, content: str) -> str:
    pattern = re.compile(rf'<meta\s+name=["\']{re.escape(name)}["\']\s+content=["\'][^"\']*["\']\s*/?>', re.I)
    tag = f'<meta name="{name}" content="{html.escape(content, quote=True)}">'
    source, count = pattern.subn(tag, source, count=1)
    if count == 0 and "</head>" in source:
        source = source.replace("</head>", tag + "\n</head>", 1)
    return source


def replace_property(source: str, prop: str, content: str) -> str:
    pattern = re.compile(rf'<meta\s+property=["\']{re.escape(prop)}["\']\s+content=["\'][^"\']*["\']\s*/?>', re.I)
    tag = f'<meta property="{prop}" content="{html.escape(content, quote=True)}">'
    source, count = pattern.subn(tag, source, count=1)
    if count == 0 and "</head>" in source:
        source = source.replace("</head>", tag + "\n</head>", 1)
    return source


def remove_script(source: str, filename: str) -> str:
    return re.sub(rf'\s*<script\b[^>]*src=["\'][^"\']*{re.escape(filename)}[^"\']*["\'][^>]*>\s*</script>\s*', "\n", source, flags=re.I | re.S)


def body_tag(attrs: str) -> str:
    attrs = re.sub(r'\sdata-proposition=["\'][^"\']*["\']', "", attrs, flags=re.I)
    match = re.search(r'class=["\']([^"\']*)["\']', attrs, flags=re.I)
    if match:
        classes = [c for c in match.group(1).split() if c not in {"email-report-home", "ai-home", "chatgpt-workspace-home"}]
        if "ai-only-home" not in classes:
            classes.append("ai-only-home")
        attrs = re.sub(r'class=["\'][^"\']*["\']', 'class="' + " ".join(classes) + '"', attrs, count=1, flags=re.I)
    else:
        attrs += ' class="ai-only-home"'
    return f'<body{attrs} data-proposition="ai-only-research">'


def purge_public_data(output: Path) -> None:
    data_dir = output / "public" / "data"
    if data_dir.exists():
        for path in sorted(data_dir.rglob("*"), reverse=True):
            if path.is_file() or path.is_symlink():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
        data_dir.rmdir()
    public_dir = output / "public"
    if public_dir.exists() and not any(public_dir.iterdir()):
        public_dir.rmdir()


def lock_public_action_pages(output: Path) -> None:
    for route in LOCKED_ROUTES:
        page = output / route / "index.html"
        if page.exists():
            page.write_text(LOCK_PAGE, encoding="utf-8")


def harden_home(output: Path) -> None:
    page = output / "index.html"
    if not page.is_file():
        raise RuntimeError(f"Homepage missing: {page}")
    assets = output / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    (assets / STYLE_NAME).write_text(CSS.strip() + "\n", encoding="utf-8")
    source = page.read_text(encoding="utf-8")
    source = re.sub(r"<title>.*?</title>", f"<title>{TITLE}</title>", source, count=1, flags=re.I | re.S)
    source = replace_meta(source, "description", DESCRIPTION)
    source = replace_meta(source, "twitter:title", TITLE)
    source = replace_meta(source, "twitter:description", DESCRIPTION)
    source = replace_property(source, "og:title", TITLE)
    source = replace_property(source, "og:description", DESCRIPTION)
    for filename in ("home-core-v1.js", "conversion-v3.js", "decision-copy-guard-v1.js", "ai-decision-view.js", "commercial-v1.js", "live-radar-v1.js", "verified-recommendations.js", "recommendation-history.js", "stock-api-client.js"):
        source = remove_script(source, filename)
    source = re.sub(r'\s*<link\b[^>]*\bdata-email-report-first\b[^>]*>\s*', "\n", source, flags=re.I)
    source = re.sub(r'\s*<link\b[^>]*\bdata-ai-only-home\b[^>]*>\s*', "\n", source, flags=re.I)
    if "</head>" not in source:
        raise RuntimeError("Homepage missing </head>")
    source = source.replace("</head>", f'<link rel="stylesheet" href="assets/{STYLE_NAME}?v=20260918-ai2" data-ai-only-home>\n</head>', 1)
    source = re.sub(r'<body\b([^>]*)>', lambda m: body_tag(m.group(1)), source, count=1, flags=re.I)
    source, nav_count = re.subn(r'<nav\b[^>]*class=["\'][^"\']*\bnav-links\b[^"\']*["\'][^>]*>.*?</nav>', NAV, source, count=1, flags=re.I | re.S)
    if nav_count != 1:
        raise RuntimeError(f"Expected one primary nav, found {nav_count}")
    source, main_count = re.subn(r'<main\b[^>]*>.*?</main>', MAIN, source, count=1, flags=re.I | re.S)
    if main_count != 1:
        raise RuntimeError(f"Expected one homepage main, found {main_count}")
    source, footer_count = re.subn(r'<div\b[^>]*class=["\'][^"\']*\bfooter-links\b[^"\']*["\'][^>]*>.*?</div>', FOOTER_LINKS, source, count=1, flags=re.I | re.S)
    if footer_count != 1:
        raise RuntimeError(f"Expected one footer links block, found {footer_count}")
    page.write_text(source, encoding="utf-8")


def rewrite_robots_and_sitemap(output: Path) -> None:
    (output / "robots.txt").write_text(
        "User-agent: *\nDisallow: /public/data/\n" + "".join(f"Disallow: /{route}/\n" for route in LOCKED_ROUTES) + "Sitemap: https://stockradar.vn/sitemap.xml\n",
        encoding="utf-8",
    )
    urls = ("/", "/bao-cao-chatgpt/", "/dieu-khoan/", "/quyen-rieng-tu/")
    body = "".join(f"<url><loc>https://stockradar.vn{u}</loc></url>" for u in urls)
    (output / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{body}</urlset>\n', encoding="utf-8")


def verify(output: Path) -> None:
    home = (output / "index.html").read_text(encoding="utf-8")
    required = ("data-ai-only-home", "AI-ONLY RESEARCH", "Không phải khuyến nghị giao dịch.", f"assets/{STYLE_NAME}")
    for marker in required:
        if marker not in home:
            raise RuntimeError(f"AI-only homepage marker missing: {marker}")
    forbidden_home = (
        "data-email-report-first", "data-home-reco-body", "data-home-live-signals", "Buy Zone", "Stop-loss",
        "ACTION ALERT", "Khuyến nghị mới nhất", "điểm mua/bán", "nhồi lệnh", "hạ tỷ trọng", "cắt lỗ/bán",
        "Đăng ký nhận báo cáo",
    )
    for marker in forbidden_home:
        if marker.lower() in home.lower():
            raise RuntimeError(f"Actionable/public-email marker survived homepage hardening: {marker}")
    data_dir = output / "public" / "data"
    if data_dir.exists() and any(data_dir.rglob("*")):
        raise RuntimeError("Public downloadable stock-data directory survived AI-only lock")
    for route in LOCKED_ROUTES:
        page = output / route / "index.html"
        if page.exists():
            text = page.read_text(encoding="utf-8")
            if "Nội dung này đang tạm khóa." not in text or 'noindex,nofollow' not in text:
                raise RuntimeError(f"Public action page not locked: {route}")
    if len(re.findall(r"<h1\b", home, flags=re.I)) != 1:
        raise RuntimeError("Homepage must contain exactly one h1")
    print("AI-only publication lock: PASS (public stock data/action pages closed; research synthesis preserved).")


def transform(output: Path) -> None:
    harden_home(output)
    purge_public_data(output)
    lock_public_action_pages(output)
    rewrite_robots_and_sitemap(output)
    verify(output)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    transform(args.output.resolve())


if __name__ == "__main__":
    main()
