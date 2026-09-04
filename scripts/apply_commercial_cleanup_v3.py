#!/usr/bin/env python3
"""Final commercial cleanup pass.

Removes residual explanatory copy from conversion-critical and dashboard routes while
preserving functional forms, data hooks, billing/auth controls and action outputs.
Also hardens the production login -> homepage flow, bridges the two Supabase browser
storage keys used by older/newer clients, and normalizes AI answer copy for clarity.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

ROUTES = ("signup", "dang-ky", "thanh-toan", "hieu-qua", "tai-khoan", "hom-nay", "khuyen-nghi")
RUNTIME_MARKER = "data-stockradar-runtime-v3"
RUNTIME_SCRIPT = r'''<script data-stockradar-runtime-v3>
(() => {
  'use strict';
  const primary = 'stockradar-auth';
  const secondary = 'sb-xamviatbxufjlpiwhebb-auth-token';

  function syncAuthStorage() {
    try {
      const current = localStorage.getItem(primary);
      const legacy = localStorage.getItem(secondary);
      if (current && current !== legacy) localStorage.setItem(secondary, current);
      else if (!current && legacy) localStorage.setItem(primary, legacy);
    } catch (_) {}
  }

  function normalizeAnswer(value) {
    let text = String(value || '').trim();
    if (!text) return text;
    text = text
      .replace(/\*\*/g, '')
      .replace(/\bAction Gate\b/gi, 'xác nhận hành động')
      .replace(/\bKHONG HANH DONG\b/gi, 'CHƯA HÀNH ĐỘNG')
      .replace(/\bTHEO DOI\b/gi, 'THEO DÕI')
      .replace(/\bWATCH\b/g, 'THEO DÕI')
      .replace(/Kết luận:\s*chưa có điểm mua hành động đã xác nhận;\s*tiếp tục THEO DÕI và chờ cấu trúc\/volume xác nhận\.?/i,
        'KẾT LUẬN: CHƯA MUA MỚI. Tiếp tục theo dõi và chờ cấu trúc giá/khối lượng xác nhận.')
      .replace(/Kết luận:\s*dùng trạng thái trên như góc nhìn nghiên cứu và chờ xác nhận hành động xác nhận trước khi hành động\.?/i,
        'KẾT LUẬN: CHƯA CÓ TÍN HIỆU HÀNH ĐỘNG ĐƯỢC XÁC NHẬN.')
      .replace(/Kết luận:\s*dùng trạng thái trên như góc nhìn nghiên cứu và chờ xác nhận hành động trước khi hành động\.?/i,
        'KẾT LUẬN: CHƯA CÓ TÍN HIỆU HÀNH ĐỘNG ĐƯỢC XÁC NHẬN.');

    const parts = text.split(/\n{2,}/).map(item => item.trim()).filter(Boolean);
    const conclusionIndex = parts.findIndex(item => /^KẾT LUẬN\s*:|^Kết luận\s*:/i.test(item));
    if (conclusionIndex > 0) {
      const [conclusion] = parts.splice(conclusionIndex, 1);
      parts.unshift(conclusion);
    }
    const researchIndex = parts.findIndex((item, index) => index > 0 && /^Góc nhìn nghiên cứu/i.test(item));
    if (researchIndex > 0) {
      const [note] = parts.splice(researchIndex, 1);
      parts.push(`Ghi chú: ${note}`);
    }
    return parts.join('\n\n');
  }

  function normalizeBubbles(root) {
    root.querySelectorAll('.sr-center-assistant .sr-center-bubble, .sr-ai-assistant .sr-ai-bubble').forEach(bubble => {
      if (bubble.dataset.stockradarNormalized === '1') return;
      const before = bubble.textContent || '';
      const after = normalizeAnswer(before);
      if (after && after !== before) bubble.textContent = after;
      bubble.dataset.stockradarNormalized = '1';
    });
  }

  syncAuthStorage();
  const start = () => {
    syncAuthStorage();
    normalizeBubbles(document);
    if (document.body) {
      new MutationObserver(records => {
        for (const record of records) {
          for (const node of record.addedNodes) {
            if (node.nodeType === 1) normalizeBubbles(node.matches?.('.sr-center-message,.sr-ai-message') ? node.parentElement || node : node);
          }
        }
      }).observe(document.body, { childList: true, subtree: true });
    }
    window.addEventListener('pageshow', syncAuthStorage);
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true });
  else start();
})();
</script>'''


def read(path: Path) -> str:
    if not path.is_file():
        raise RuntimeError(f"Missing commercial cleanup route: {path}")
    return path.read_text(encoding="utf-8")


def cleanup_signup(source: str) -> str:
    # Remove the nested onboarding explanation without touching the following plan summary/form.
    source, count = re.subn(
        r'\s*<div\b[^>]*class=["\'][^"\']*\bpremium-email-onboarding-v1\b[^"\']*["\'][^>]*>.*?</div>\s*</div>\s*(?=<div\b[^>]*class=["\'][^"\']*\bconversion-premium-summary\b)',
        "\n",
        source,
        count=1,
        flags=re.I | re.S,
    )
    if count != 1:
        raise RuntimeError("Premium onboarding explanation block not found")
    source = source.replace("Free 10 câu AI/ngày · Premium không giới hạn.", "Free 10 câu/ngày · Premium không giới hạn.")
    source = source.replace("Có thể bật/tắt từng loại email.", "Email Premium là tùy chọn.")
    return source


def cleanup_plans(source: str) -> str:
    source = re.sub(
        r'<p class="plan-price-note">.*?</p>',
        '<p class="plan-price-note">* Email Premium được bật khi kênh gửi chính thức sẵn sàng.</p>',
        source,
        count=1,
        flags=re.I | re.S,
    )
    source = re.sub(
        r'<p class="plan-legal">.*?</p>',
        '<p class="plan-legal">199K/30 ngày · Không tự gia hạn · Kích hoạt sau khi thanh toán được xác minh.</p>',
        source,
        count=1,
        flags=re.I | re.S,
    )
    return source


def cleanup_checkout(source: str) -> str:
    source = source.replace("Tài khoản nhận tiền vẫn là VPBank 0934389822", "Chưa có mã SR")
    source = source.replace(
        "Nếu hệ thống tạm thời chưa tạo được mã SR riêng, chưa chuyển khoản cho đến khi mã được hiển thị. Điều này giúp StockRadar đối soát đúng tài khoản Premium.",
        "Chỉ chuyển khoản khi mã SR đã hiển thị.",
    )
    return source


def cleanup_performance(source: str) -> str:
    source = source.replace("Không cherry-pick", "Mẫu thực tế")
    source = source.replace("Chưa kích hoạt ≠ đã mua", "Chưa kích hoạt ≠ giao dịch")
    source = source.replace("So cùng VN-Index", "So với VN-Index")
    source = source.replace("Có dấu thời gian", "Có thời gian")
    source, count = re.subn(
        r'<div class="conversion-performance-head">.*?</div><div data-performance-summary>',
        '<div class="conversion-performance-head"><h2>Kết quả thực tế</h2></div><div data-performance-summary>',
        source,
        count=1,
        flags=re.I | re.S,
    )
    if count != 1:
        raise RuntimeError("Performance explainer block not found")
    return source


def cleanup_account(source: str) -> str:
    source = source.replace(
        "Chỉ hiển thị metadata vận hành của chính tài khoản; không hiển thị provider secret hoặc nội dung email.",
        "Chỉ hiển thị trạng thái của tài khoản này.",
    )
    source = source.replace("Theo dõi đúng thứ bạn quan tâm", "Danh sách theo dõi")
    source = source.replace("Có thể nhập giá vốn và tỷ trọng ước tính nếu muốn cá nhân hóa sâu hơn.", "Giá vốn và tỷ trọng là tùy chọn.")
    source = source.replace("Có thể bật cảnh báo trên từng mã.", "Bật cảnh báo trên từng mã nếu cần.")
    return source


def cleanup_today(source: str) -> str:
    source = source.replace("Bảng Hôm nay hiển thị theo trạng thái tài khoản đã xác định.", "Đang tải…")
    source = source.replace(
        "StockRadar sẽ ưu tiên mã đang sở hữu, watchlist và cảnh báo đã bật trên chính tài khoản của bạn.",
        "Ưu tiên mã đang sở hữu, watchlist và cảnh báo đã bật.",
    )
    return source


def cleanup_recommendations(source: str) -> str:
    source = source.replace("Tín hiệu hành động đã được StockRadar phát hành.", "Tín hiệu đã phát hành.")
    return source


def force_login_home(output: Path) -> None:
    page = output / "dang-nhap" / "index.html"
    source = read(page)
    source, count = re.subn(
        r"if\s*\(!url\.searchParams\.has\('next'\)\)\s*\{\s*url\.searchParams\.set\('next',\s*'hom-nay/'\);\s*history\.replaceState\(null,\s*'',\s*url\);\s*\}",
        "url.searchParams.set('next', new URL('', document.baseURI).toString());\n      history.replaceState(null, '', url);",
        source,
        count=1,
        flags=re.S,
    )
    if count != 1:
        raise RuntimeError("Login default redirect block not found")
    page.write_text(source, encoding="utf-8")


def inject_runtime(output: Path) -> None:
    for page in output.rglob("*.html"):
        source = page.read_text(encoding="utf-8")
        if RUNTIME_MARKER in source:
            continue
        if "</head>" not in source:
            continue
        source = source.replace("</head>", f"{RUNTIME_SCRIPT}\n</head>", 1)
        page.write_text(source, encoding="utf-8")


def process(output: Path, route: str) -> None:
    page = output / route / "index.html"
    source = read(page)
    transform = {
        "signup": cleanup_signup,
        "dang-ky": cleanup_plans,
        "thanh-toan": cleanup_checkout,
        "hieu-qua": cleanup_performance,
        "tai-khoan": cleanup_account,
        "hom-nay": cleanup_today,
        "khuyen-nghi": cleanup_recommendations,
    }[route]
    page.write_text(transform(source), encoding="utf-8")


def verify(output: Path) -> None:
    pages = {route: read(output / route / "index.html") for route in ROUTES}
    forbidden = {
        "signup": ("premium-email-onboarding-v1", "Để StockRadar canh mã thay bạn"),
        "dang-ky": ("production đạt chuẩn vận hành", "Gói 199K/30 ngày hiện được vận hành"),
        "thanh-toan": ("Tài khoản nhận tiền vẫn là VPBank", "Điều này giúp StockRadar đối soát"),
        "hieu-qua": ("Hãy nhìn dữ liệu thực tế trước khi quyết định trả phí", "KẾT QUẢ TRƯỚC, CÁCH ĐO SAU"),
        "tai-khoan": ("metadata vận hành", "cá nhân hóa sâu hơn"),
        "hom-nay": ("Bảng Hôm nay hiển thị theo trạng thái tài khoản đã xác định",),
        "khuyen-nghi": ("Tín hiệu hành động đã được StockRadar phát hành",),
    }
    for route, terms in forbidden.items():
        low = pages[route].lower()
        for term in terms:
            if term.lower() in low:
                raise RuntimeError(f"Residual explanatory copy survived on {route}: {term}")

    required = {
        "signup": ("data-auth-signup-form", "data-signup-plan-name", "data-signup-submit-label"),
        "dang-ky": ("data-plan-free", "data-plan-premium", "data-plan-comparison"),
        "thanh-toan": ("data-checkout-confirm", "vpbank-qr-static.svg", "0934389822", "data-checkout-reference"),
        "hieu-qua": ("data-performance-summary",),
        "tai-khoan": ("data-product-email-preferences", "data-account-personalization", "data-account-watchlist-form"),
        "hom-nay": ("data-paid-dashboard",),
        "khuyen-nghi": ("data-recommendations", "data-recommendation-journal"),
    }
    for route, markers in required.items():
        source = pages[route]
        for marker in markers:
            if marker not in source:
                raise RuntimeError(f"Functional marker missing after cleanup: {route}: {marker}")

    login = read(output / "dang-nhap" / "index.html")
    if "url.searchParams.set('next', new URL('', document.baseURI).toString())" not in login:
        raise RuntimeError("Login no longer forces successful sign-in back to homepage")
    if "'hom-nay/'" in login and "searchParams.set('next'" in login:
        raise RuntimeError("Legacy login redirect to hom-nay survived")

    home = read(output / "index.html")
    if RUNTIME_MARKER not in home or "stockradar-auth" not in home or "sb-xamviatbxufjlpiwhebb-auth-token" not in home:
        raise RuntimeError("Homepage auth continuity bridge missing")
    if "normalizeAnswer" not in home or "KẾT LUẬN: CHƯA MUA MỚI" not in home:
        raise RuntimeError("Homepage AI clarity normalizer missing")

    print("Commercial cleanup v3: PASS (copy cleanup + auth continuity + AI clarity hardening)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    for route in ROUTES:
        process(output, route)
    force_login_home(output)
    inject_runtime(output)
    verify(output)


if __name__ == "__main__":
    main()
