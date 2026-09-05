"""Build the recommendation route from the audited public ledger, before JavaScript runs."""
from datetime import datetime, timezone, timedelta
from html import escape
import json
from pathlib import Path
import re

VN = timezone(timedelta(hours=7))


def timestamp(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(VN).strftime('%H:%M %d/%m/%Y')


def day(value):
    return '/'.join(str(value).split('-')[::-1]) if value else '—'


def money(value):
    return f'{value:,.0f}đ'.replace(',', '.') if value is not None else '—'


def change(value):
    return f'{value:+.2f}%'.replace('.', ',') if value is not None else '—'


def build_content(data):
    if data.get('schema_version') != 'STOCKRADAR_VERIFIED_HISTORY_V1':
        raise ValueError('Verified recommendation history is missing or incompatible')
    items = sorted(data['items'], key=lambda r: datetime.fromisoformat(r['first_sent_at']), reverse=True)
    summary = data['summary']
    headings = ['Mã', 'Thời gian khuyến nghị', 'Giá khuyến nghị', 'Giá hiện tại', 'Lãi/lỗ tạm tính', 'Trạng thái']
    rows, details, events = [], [], []
    for row in items:
        ticker = escape(row['ticker'])
        status = row['status']
        states = {'NO_SELL_EMAIL_FOUND': 'Chưa ghi nhận bán', 'SELL_EMAIL_RECORDED': 'Đã ghi nhận bán'}
        if status not in states:
            raise ValueError(f'Unknown recommendation status: {status}')
        state = states[status]
        gain = row.get('price_change_pct')
        tone = 'vr-up' if gain is not None and gain > 0 else 'vr-down' if gain is not None and gain < 0 else ''
        values = [f'<a class="vr-ticker" href="khuyen-nghi/#history-{ticker}" data-rec-detail>{ticker}</a>',
            f'<b>{timestamp(row["signal_at"])}</b><small>Gửi: {timestamp(row["first_sent_at"])}</small>',
            f'<b>{money(row.get("reference_price"))}</b>',
            f'<b>{money(row.get("latest_price"))}</b><small>{day(row.get("price_date"))}</small>',
            f'<b class="{tone}">{change(gain)}</b>', f'<span class="vr-state">{state}</span>']
        cells = ''.join(f'<td data-label="{escape(label)}">{value}</td>' for label, value in zip(headings, values))
        rows.append(f'<tr data-verified-row data-ticker="{ticker}" data-verified-lifecycle="{escape(status)}">{cells}</tr>')
        detail_events = []
        for event in sorted(row['timeline'], key=lambda e: e['sent_at'], reverse=True):
            kind = {'BUY': 'Báo mua', 'UPDATE': 'Điều chỉnh', 'SELL': 'Báo bán'}.get(event['kind'], 'Cập nhật')
            zone = ' – '.join(money(v) for v in event.get('buy_zone', []))
            near = ' – '.join(money(v) for v in event.get('near_target', []))
            detail_events.append(f'<li><b>{kind} · {timestamp(event["signal_at"])}</b><p>Gửi lúc {timestamp(event["sent_at"])} đến {event["recipient_count"]} địa chỉ.</p><p>Vùng mua trong thư: {zone}. Cắt lỗ: {money(event.get("stop_loss"))}. Mục tiêu gần: {near}.</p><p>{escape(event.get("note", ""))}</p></li>')
            events.append((event['sent_at'], f'<li data-verified-event data-ticker="{ticker}"><time>{timestamp(event["sent_at"])}</time><strong>{ticker} · {kind}</strong><span>{zone} · Cắt lỗ {money(event.get("stop_loss"))}</span></li>'))
        details.append(f'<details class="vr-detail" id="history-{ticker}" data-verified-detail data-ticker="{ticker}"><summary>{ticker} · Các lần gửi và điều chỉnh</summary><p>Nội dung đã gửi trước đây; không phải điểm mua mới hôm nay.</p><ol>{"".join(detail_events)}</ol><a href="co-phieu/?ticker={ticker}" class="button button-secondary button-small">Tra cứu {ticker} hôm nay →</a></details>')
    table_rows = ''.join(rows) or '<tr><td colspan="6">Chưa có khuyến nghị được xác minh trong lịch sử này.</td></tr>'
    journal = ''.join(html for _, html in sorted(events, key=lambda e: e[0], reverse=True))
    return f'''<main id="content" data-verified-recommendations>
      <section class="page-heading compact-heading"><div class="container"><h1>Khuyến nghị StockRadar</h1><p>Mới nhất trước.</p></div></section>
      <section class="container vr-workspace">
        <div class="vr-metrics"><div><span>Đã báo mua</span><b>{summary['tickers']} mã</b></div><div><span>Chưa ghi nhận bán</span><b>{summary['without_sell_email']} mã</b></div><div><span>Đã ghi nhận bán</span><b>{summary['with_sell_email']} mã</b></div></div>
        <fieldset class="vr-controls" data-verified-controls disabled><legend>Lọc khuyến nghị</legend><label>Mã cổ phiếu<input type="search" maxlength="3" placeholder="VD: VHM" data-verified-search autocomplete="off"></label><label>Trạng thái<select data-verified-status><option value="">Tất cả</option><option value="NO_SELL_EMAIL_FOUND">Chưa ghi nhận bán</option><option value="SELL_EMAIL_RECORDED">Đã ghi nhận bán</option></select></label><button type="button" class="button button-secondary button-small" data-verified-reset>Xóa lọc</button></fieldset>
        <div class="vr-table-wrap" data-recommendations><table class="vr-table"><caption data-verified-count>{len(items)} mã khuyến nghị</caption><thead><tr>{''.join('<th scope="col">'+h+'</th>' for h in headings)}</tr></thead><tbody>{table_rows}</tbody></table><p class="vr-empty" data-verified-empty hidden>Không có mã khớp bộ lọc. Chọn “Tất cả” hoặc xóa mã.</p></div>
        <p class="vr-note">Giá đóng cửa {day(data['as_of_date'])}. Lãi/lỗ so với giá báo mua đầu, chưa tính phí, thuế, quyền; chưa chốt.</p>
        <div class="vr-links"><a href="hieu-qua/">Hiệu quả từng mã →</a><a href="hieu-qua/#review-2026-08">Rà soát tháng 8 →</a><a href="radar5/">Radar hôm nay →</a></div>
        <section class="vr-details" aria-label="Chi tiết khuyến nghị">{''.join(details)}</section>
        <details class="vr-detail" id="nhat-ky"><summary>NHẬT KÝ TRẠNG THÁI · {len(events)} lần gửi</summary><ol class="vr-journal" data-recommendation-journal>{journal}</ol></details>
        <details class="vr-detail"><summary>Nguồn và mốc cập nhật</summary><p>Đã đối chiếu email StockRadar đến {day(data['mail_search_through'])}. Thời gian khuyến nghị là lúc phát hiện; giờ gửi email ghi riêng. DCM buổi chiều là điều chỉnh, không đếm thành một khuyến nghị mới.</p><p>“Chưa ghi nhận bán” phản ánh lịch sử đã kiểm tra, chưa khẳng định nên tiếp tục giữ. Rà soát kỹ thuật tháng 8 được trình bày riêng trong trang Hiệu quả, không cộng vào khuyến nghị đã gửi.</p></details>
      </section></main>'''


def render_page(source: str, output: Path) -> str:
    data = json.loads((output / 'public/data/recommendation-history.json').read_text(encoding='utf-8'))
    content = build_content(data)
    source, count = re.subn(r'<main\b[^>]*>.*?</main>', lambda _: content, source, count=1, flags=re.S)
    if count != 1:
        raise ValueError('Recommendation main section missing')
    source = re.sub(r'<section class="market-tape".*?</section>', '', source, count=1, flags=re.S)
    source = re.sub(r'<nav class="product-subnav".*?</nav>', '', source, count=1, flags=re.S)
    source = re.sub(r'assets/app\.js\?[^"\s]+', 'assets/app.js?v=20260905-verified-page', source)
    return source.replace('</head>', '<link rel="stylesheet" href="assets/verified-recommendations.css?v=1"><script src="assets/verified-recommendations.js?v=1" defer></script></head>', 1)
