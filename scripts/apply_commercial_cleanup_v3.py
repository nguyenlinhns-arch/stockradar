#!/usr/bin/env python3
"""Final commercial cleanup pass.

Removes residual explanatory copy from conversion-critical and dashboard routes while
preserving functional forms, data hooks, billing/auth controls and action outputs.
Also hardens login-to-home continuity, reconciles legacy/current Supabase browser
storage keys, and normalizes AI answer copy for clearer decisions.
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
      const migrated = 'stockradar-auth-migrated-v1';
      if (localStorage.getItem(migrated)) return;
      const current = localStorage.getItem(primary);
      const legacy = localStorage.getItem(secondary);
      if (!current && legacy) localStorage.setItem(primary, legacy);
      localStorage.removeItem(secondary);
      localStorage.setItem(migrated, '1');
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
          for (const added of record.addedNodes) {
            if (added.nodeType !== 1) continue;
            const root = added.matches?.('.sr-center-message,.sr-ai-message') ? (added.parentElement || added) : added;
            normalizeBubbles(root);
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
    source = source.replace(
        "Email chỉ hoạt động khi kênh production sẵn sàng.",
        "Email Premium được bật khi kênh gửi chính thức sẵn sàng.",
    )
    source = re.sub(
        r'<p class="plan-price-note">.*?</p>',
        '<p class="plan-price-note">* Email chưa bật. Khi sẵn sàng: bản tin 09:00; cảnh báo sau lượt quét 10:30 · 11:15 · 13:30 · 14:15 (giờ VN), khi tín hiệu được xác nhận. Cập nhật theo lượt quét.</p>',
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
    source = source.replace('<div data-performance-summary>', '<div data-performance-summary hidden>', 1)
    source = source.replace('<div data-performance-summary hidden>', '<div data-alert-history><p>Đang tải lịch sử email và kết quả từng mã…</p></div><div data-performance-summary hidden>', 1)
    source = source.replace('Kết quả thực tế</h2>', 'Theo dõi khuyến nghị</h2>')
    source = source.replace('</head>', '<link rel="stylesheet" href="assets/recommendation-history.css?v=1"><script src="assets/recommendation-history.js?v=2" defer></script></head>', 1)
    return source


def cleanup_account(source: str) -> str:
    replacements = (
        ("Chỉ hiển thị metadata vận hành của chính tài khoản; không hiển thị provider secret hoặc nội dung email.", "Chỉ hiển thị trạng thái của tài khoản này."),
        ("Theo dõi đúng thứ bạn quan tâm", "Danh sách theo dõi"),
        ("CÁ NHÂN HÓA", "WATCHLIST & VỊ THẾ"),
        ("ƯU TIÊN PHÂN TÍCH", "ƯU TIÊN"),
        ("Có thể nhập giá vốn và tỷ trọng ước tính nếu muốn cá nhân hóa sâu hơn.", "Giá vốn và tỷ trọng là tùy chọn."),
        ("Có thể bật cảnh báo trên từng mã.", "Bật cảnh báo trên từng mã nếu cần."),
        ("Trial/Premium · email production sẵn sàng.", "Theo quyền Premium."),
        ("Free chỉ nhận email hệ thống cần thiết cho tài khoản; Trial/Paid mới có email nội dung Premium và Action Alert.", "Free: email tài khoản · Premium: báo cáo và Action Alert."),
        ("Bản chủ động theo watchlist và việc cần chú ý, chỉ dành cho Trial/Paid khi delivery production đạt chuẩn.", "Daily 09:00 theo watchlist."),
        ("Cần tài khoản Trial/Paid, email đã xác minh và hệ thống delivery production đã được kích hoạt.", "Theo quyền Premium."),
        ("dữ liệu cá nhân được bảo vệ bằng Supabase RLS.", "Dữ liệu cá nhân chỉ hiển thị trong tài khoản của bạn."),
        ("Có thể để trống; hệ thống sẽ dùng thứ tự trung tính.", "Không bắt buộc."),
        ("Tôi đang sở hữu mã này — dùng để tách riêng quyết định “đang nắm giữ” khỏi “mua mới”.", "Tôi đang sở hữu mã này"),
        ("Bạn có thể đổi lựa chọn hoặc rút đăng ký email bất kỳ lúc nào.", "Có thể thay đổi bất kỳ lúc nào."),
    )
    for before, after in replacements:
        source = source.replace(before, after)

    source = re.sub(
        r'<div class="auth-security-note"><strong>Quyền email:</strong>\s*<span data-email-pref-eligibility>.*?</span>.*?</div>',
        '<div class="auth-security-note"><strong>Quyền email:</strong> <span data-email-pref-eligibility>Đang kiểm tra…</span></div>',
        source,
        count=1,
        flags=re.I | re.S,
    )
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
        r"if\s*\(!url\.searchParams\.has\('next'\)\)\s*\{[^{}]*url\.searchParams\.set\('next',[^;]*;\s*history\.replaceState\(null,\s*'',\s*url\);\s*\}",
        "url.searchParams.set('next', new URL('', document.baseURI).toString());\n      history.replaceState(null, '', url);",
        source,
        count=1,
        flags=re.S,
    )
    if count != 1:
        raise RuntimeError("Login redirect block not found")
    page.write_text(source, encoding="utf-8")


def inject_runtime(output: Path) -> None:
    for page in output.rglob("*.html"):
        source = page.read_text(encoding="utf-8")
        source = re.sub(r'@supabase/supabase-js@2(?=["\'])', '@supabase/supabase-js@2.95.0', source)
        seen = set()
        def unique_script(match):
            ref = match.group(1).split('?')[0]
            if ref in seen:
                return ''
            seen.add(ref)
            return match.group(0)
        source = re.sub(r'<script\b[^>]*src=["\']([^"\']+)["\'][^>]*>\s*</script>', unique_script, source, flags=re.I)
        page.write_text(source, encoding='utf-8')
        if RUNTIME_MARKER in source or "</head>" not in source:
            continue
        page.write_text(source.replace("</head>", f"{RUNTIME_SCRIPT}\n</head>", 1), encoding="utf-8")


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
        "dang-ky": ("production đạt chuẩn vận hành", "Gói 199K/30 ngày hiện được vận hành", "kênh production"),
        "thanh-toan": ("Tài khoản nhận tiền vẫn là VPBank", "Điều này giúp StockRadar đối soát"),
        "hieu-qua": ("Hãy nhìn dữ liệu thực tế trước khi quyết định trả phí", "KẾT QUẢ TRƯỚC, CÁCH ĐO SAU"),
        "tai-khoan": ("metadata vận hành", "provider secret", "cá nhân hóa sâu hơn", "delivery production", "email production", "Supabase RLS"),
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
        raise RuntimeError("Successful login is not forced back to the homepage")
    if "url.searchParams.set('next', 'hom-nay/')" in login:
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
