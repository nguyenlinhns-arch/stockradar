// Presentation only: prices and actions must come from the approved report contract.
type Row = Record<string, any>;
const esc = (v: unknown) => String(v ?? '').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;');
const present = (v: unknown) => v !== null && v !== undefined && v !== '' && typeof v !== 'boolean';
export function vietnamTime(v: unknown): string {
  if (!present(v) || typeof v !== 'string' || !/^\d{4}-\d{2}-\d{2}T.*(?:Z|[+-]\d{2}:\d{2})$/.test(v)) return 'Chưa có thời gian xác nhận';
  const d = new Date(v);
  return Number.isFinite(d.getTime()) ? new Intl.DateTimeFormat('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).format(d) + ' (giờ VN)' : 'Chưa có thời gian xác nhận';
}
export function price(v: unknown): string {
  const n = present(v) && ['number','string'].includes(typeof v) ? Number(v) : NaN;
  return Number.isFinite(n) && n > 0 ? n.toLocaleString('vi-VN',{maximumFractionDigits:0}) + 'đ' : 'Chưa xác nhận';
}
export function action(v: unknown): string {
  return ({WAIT:'Theo dõi',WATCH:'Theo dõi',BUY:'Mua',MUA:'Mua',HOLD:'Giữ và quan sát',ADD:'Mua thêm',REDUCE:'Bán bớt',SELL:'Bán'} as Row)[String(v || '').toUpperCase()] || 'Chưa xác nhận';
}
const range = (v: any) => Array.isArray(v) ? `${price(v[0])} – ${price(v[1])}` : v && typeof v === 'object' ? `${price(v.low)} – ${price(v.high)}` : price(v);
const text = (v: any) => Array.isArray(v) ? v.join('; ') : typeof v === 'string' && v.trim() ? v : 'Chưa xác nhận';
const row = (label: string, value: unknown) => `<tr><td style="padding:9px;border-bottom:1px solid #e2e8f0;color:#64748b">${esc(label)}</td><td style="padding:9px;border-bottom:1px solid #e2e8f0;font-weight:700">${esc(value)}</td></tr>`;
const table = (body: string) => `<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;font-size:14px">${body}</table>`;
const link = (website: string, ticker?: string) => `${website.replace(/\/$/,'')}/${ticker ? `co-phieu/?ticker=${encodeURIComponent(ticker)}` : 'tai-khoan/'}`;
const button = (url: string) => `<p><a href="${esc(url)}" style="display:inline-block;background:#0b1f33;color:#fff;text-decoration:none;padding:12px 18px;border-radius:9px;font-weight:700">XEM TRẠNG THÁI MỚI NHẤT</a></p>`;
export function actionBody(payload: Row, website: string): string {
  const c = payload.decision_card && typeof payload.decision_card === 'object' ? payload.decision_card : payload;
  const ticker = String(c.ticker || payload.ticker || '');
  const rr = present(c.risk_reward) ? Number(c.risk_reward) : NaN;
  const reasons = Array.isArray(payload.reasons) ? payload.reasons.slice(0,3) : [];
  return `<div style="font-size:12px;font-weight:700;color:#64748b">CẢNH BÁO CỔ PHIẾU</div><h1 style="font-size:26px">${esc(ticker)} · ${esc(action(c.current_state || payload.current_state))}</h1>` + table(
    row('Thay đổi',`${action(c.previous_state || payload.previous_state)} → ${action(c.current_state || payload.current_state)}`) +
    row('Xác nhận lúc',vietnamTime(c.evaluated_at)) + row('Nếu chưa sở hữu',action(c.new_position_decision)) + row('Nếu đang nắm giữ',action(c.holding_decision)) +
    row('Giá tham chiếu',price(c.reference_price)) + row('Vùng giá mua',range(c.buy_zone)) + row('Giá cắt lỗ',price(c.stop)) + row('Giá mục tiêu',price(c.target)) +
    row('Lãi kỳ vọng so với lỗ dự kiến',Number.isFinite(rr) && rr > 0 ? `${rr.toLocaleString('vi-VN',{maximumFractionDigits:2})} lần` : 'Chưa xác nhận') +
    row('Kiểm tra kế tiếp dự kiến',vietnamTime(c.next_review))) +
    (reasons.length ? `<p><strong>Lý do:</strong> ${reasons.map(esc).join('; ')}</p>` : '') +
    `<p><strong>Điều kiện hủy khuyến nghị:</strong> ${esc(text(c.invalidation))}</p><p>Không mua cao hơn vùng giá mua. Nếu mở email muộn, hãy xem trạng thái mới nhất trước khi đặt lệnh.</p>${button(link(website,ticker))}`;
}
export function dailyBody(payload: Row, website: string): string {
  const opportunities = Array.isArray(payload.opportunities) ? payload.opportunities.filter((i: Row)=>i.publish_status==='PUBLISHED' && i.action==='MUA') : [];
  const changes = Array.isArray(payload.watchlist_changes) ? payload.watchlist_changes : [];
  const items = opportunities.map((i: Row)=>`<h2 style="font-size:18px">${esc(i.ticker)} · Mua</h2>` + table(
    row('Giá tham chiếu',price(i.reference_price)) + row('Vùng giá mua',range(i.buy_zone)) + row('Giá cắt lỗ',price(i.stop_loss)) + row('Giá mục tiêu',price(i.target)) + row('Xác nhận lúc',vietnamTime(i.confirmed_at))) + button(link(website,i.ticker))).join('');
  const changeRows = changes.map((i: Row)=>row(String(i.ticker),`${action(i.previous_state)} → ${action(i.current_state)}; ${vietnamTime(i.evaluated_at)}`)).join('');
  return `<div style="font-size:12px;font-weight:700;color:#64748b">BẢN TIN CỔ PHIẾU</div><h1 style="font-size:26px">${esc(payload.headline || (opportunities.length ? `${opportunities.length} mã được xác nhận mua` : 'Chưa có mã được xác nhận mua'))}</h1><p>Lập bản tin lúc ${esc(vietnamTime(payload.generated_at))}<br>Dữ liệu rà soát lúc ${esc(vietnamTime(payload.evaluated_at))}</p>` +
    (items || '<p>Chưa có khuyến nghị mua đủ điều kiện công bố trong lần rà soát này.</p>') +
    (changeRows ? `<h2 style="font-size:18px">Thay đổi trong danh sách của bạn</h2>${table(changeRows)}` : '') +
    `<p>Kiểm tra kế tiếp dự kiến: ${esc(vietnamTime(payload.next_review_at))}.</p>${button(link(website))}`;
}
