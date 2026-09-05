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
  return ({WAIT:'Theo dõi',WATCH:'Theo dõi',BUY:'Mua',MUA:'Mua',HOLD:'Giữ và quan sát',GIỮ:'Giữ và quan sát',ADD:'Mua thêm',TĂNG:'Mua thêm',REDUCE:'Bán bớt',GIẢM:'Bán bớt',SELL:'Bán',BÁN:'Bán'} as Row)[String(v || '').toUpperCase()] || 'Chưa xác nhận';
}
const pct=(v:any)=>present(v)&&Number.isFinite(Number(v))?`${Number(v).toLocaleString('vi-VN',{maximumFractionDigits:1})}%`:'Chưa xác nhận';
export function emailSubject(payload:Row,kind:string):string {
  const c=payload.decision_card||payload,at=kind==='EVENT_ALERT'?c.evaluated_at:payload.generated_at;
  const stamp=vietnamTime(at),match=stamp.match(/(\d{2}:\d{2}).*?(\d{2}\/\d{2}\/\d{4})/);
  if(kind!=='EVENT_ALERT')return `[StockRadar][${match?.[2]||'Ngày chưa xác nhận'}] Báo cáo thị trường hàng ngày`;
  const state=String(c.current_state||payload.current_state||'').toUpperCase();
  const setup=String(c.setup||'').toUpperCase();
  const label=['SELL','BÁN'].includes(state)?'BÁN':state==='REDUCE'||state==='GIẢM'?'HẠ TỶ TRỌNG':state==='ADD'||state==='TĂNG'?'NHỒI LỆNH':
    ['POCKET_PIVOT','EARLY_BREAKOUT','CONFIRMED_BREAKOUT','RETEST'].includes(setup)?setup.replaceAll('_',' '):action(state).toUpperCase();
  return `[${label}] ${String(c.ticker||payload.ticker||'').replace(/[^A-Z0-9]/g,'')} — ${match?.[1]||'Giờ chưa xác nhận'} ${match?.[2]||''} — Giá ${price(c.reference_price)}`;
}
const range = (v: any) => Array.isArray(v) ? `${price(v[0])} – ${price(v[1])}` : v && typeof v === 'object' ? `${price(v.low)} – ${price(v.high)}` : price(v);
const text = (v: any) => Array.isArray(v) ? v.join('; ') : typeof v === 'string' && v.trim() ? v : 'Chưa xác nhận';
const row = (label: string, value: unknown) => `<tr><td style="padding:9px;border-bottom:1px solid #e2e8f0;color:#64748b">${esc(label)}</td><td style="padding:9px;border-bottom:1px solid #e2e8f0;font-weight:700">${esc(value)}</td></tr>`;
const table = (body: string) => `<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;font-size:14px">${body}</table>`;
const link = (website: string, ticker?: string, campaign='action_alert') => `${website.replace(/\/$/,'')}/${ticker ? `co-phieu/?ticker=${encodeURIComponent(ticker)}&` : 'tai-khoan/?'}utm_source=stockradar_email&utm_campaign=${campaign}`;
const button = (url: string) => `<p><a href="${esc(url)}" style="display:inline-block;background:#0b1f33;color:#fff;text-decoration:none;padding:12px 18px;border-radius:9px;font-weight:700">Phân tích chi tiết bằng AI StockRadar</a></p>`;
const number = (v: any): number | null => price(v) === 'Chưa xác nhận' ? null : Number(v);
const horizonName = (v: any) => ({SHORT_TERM:'ngắn hạn',MEDIUM_TERM:'3–6 tháng',LONG_TERM:'12 tháng',ACCUMULATION:'tích sản'} as Row)[String(v || '')] || 'theo thời hạn báo cáo';
function primaryTarget(c: Row) {
  if (c.horizon === 'MEDIUM_TERM') return c.target_3_6m;
  if (c.horizon === 'LONG_TERM') return c.target_12m;
  if (c.horizon === 'ACCUMULATION') return c.target_price;
  return c.target_near ?? c.target ?? c.target_price;
}
function pricePlanRows(c: Row): string {
  return row('Thời hạn',horizonName(c.horizon)) + row('Giá cắt lỗ',price(c.stop_loss ?? c.stop)) +
    row(`Mục tiêu dự kiến ${horizonName(c.horizon)}`,price(primaryTarget(c))) +
    row('Mục tiêu dự kiến ngắn hạn',price(c.target_near ?? (c.horizon === 'SHORT_TERM' || !c.horizon ? c.target : null))) +
    row('Mục tiêu dự kiến 3–6 tháng',price(c.target_3_6m)) + row('Mục tiêu dự kiến 12 tháng',price(c.target_12m));
}
// A buy/add alert without a usable loss limit and a target for its own horizon
// must never reach the provider. Exit alerts remain deliverable without a target.
export function emailPricePlanError(payload: Row, kind: string): string | null {
  const c = payload.decision_card && typeof payload.decision_card === 'object' ? payload.decision_card : payload;
  const plans = kind === 'DAILY_BRIEF' ? (Array.isArray(payload.opportunities) ? payload.opportunities.filter((x: Row)=>x.publish_status==='PUBLISHED' && x.action==='MUA') : [])
    : kind === 'EVENT_ALERT' && ['BUY','MUA','ADD','TĂNG'].includes(String(c.current_state || payload.current_state).toUpperCase()) ? [c] : [];
  for (const p of plans) {
    const zone = p.buy_zone;
    const low = number(Array.isArray(zone) ? zone[0] : zone?.low), high = number(Array.isArray(zone) ? zone[1] : zone?.high);
    const stop = number(p.stop_loss ?? p.stop), target = number(primaryTarget(p));
    if (stop == null || target == null || low == null || high == null) return 'BUY_EMAIL_MISSING_TARGET_STOP_OR_ENTRY';
    if (low > high || stop >= low || target <= high) return 'BUY_EMAIL_INVALID_TARGET_STOP_OR_ENTRY';
    if(kind==='EVENT_ALERT') {
      const size=number(p.position_initial_pct),rr=number(p.risk_reward);
      if(!size||size>=100||!rr||!['POCKET_PIVOT','EARLY_BREAKOUT','CONFIRMED_BREAKOUT','RETEST'].includes(String(p.setup)))return 'BUY_EMAIL_MISSING_SETUP_SIZING_OR_RR';
    }
  }
  return null;
}
export function actionBody(payload: Row, website: string): string {
  const c = payload.decision_card && typeof payload.decision_card === 'object' ? payload.decision_card : payload;
  const ticker = String(c.ticker || payload.ticker || '');
  const rr = present(c.risk_reward) ? Number(c.risk_reward) : NaN;
  const reasons = Array.isArray(payload.reasons) ? payload.reasons.slice(0,3) : [];
  const state=String(c.current_state||payload.current_state||'').toUpperCase();
  const buying=['BUY','MUA','ADD','TĂNG'].includes(state);
  const headline=buying?`${['ADD','TĂNG'].includes(state)?'MUA THÊM':'MUA THĂM DÒ'} ${pct(c.position_initial_pct)}`:action(state).toUpperCase();
  return `<h1 style="font-size:23px">HÀNH ĐỘNG: ${esc(headline)}</h1><h2 style="font-size:20px">${esc(ticker)} · ${esc(action(state))}</h2>` + table(
    row('Thay đổi',`${action(c.previous_state || payload.previous_state)} → ${action(c.current_state || payload.current_state)}`) +
    row('Xác nhận lúc',vietnamTime(c.evaluated_at)) + row('Nếu chưa sở hữu',action(c.new_position_decision)) + row('Nếu đang nắm giữ',action(c.holding_decision)) +
    row('Giá tham chiếu',price(c.reference_price)) + row('Vùng giá mua',range(c.buy_zone)) + pricePlanRows(c) +
    row('Dạng điểm mua',text(c.setup)) + row('Tỷ trọng đề xuất',pct(c.position_initial_pct)) +
    row('Ngày dữ liệu',text(c.as_of_date)) + row('Thời gian nguồn',vietnamTime(c.source_updated_at)) + row('Trạng thái nguồn',text(c.data_freshness)) +
    row('Dư địa tăng / rủi ro giảm',`${pct(c.upside_pct)} / ${pct(c.downside_pct)}`) + row('Thời gian kỳ vọng',text(c.expected_holding_period)) +
    row('Lãi kỳ vọng so với lỗ dự kiến',Number.isFinite(rr) && rr > 0 ? `${rr.toLocaleString('vi-VN',{maximumFractionDigits:2})} lần` : 'Chưa xác nhận') +
    row('Kiểm tra kế tiếp dự kiến',vietnamTime(c.next_review))) +
    (reasons.length ? `<p><strong>Lý do:</strong> ${reasons.map(esc).join('; ')}</p>` : '') +
    `<p><strong>Điều kiện hủy khuyến nghị:</strong> ${esc(text(c.invalidation))}</p><p>Mục tiêu là mức dự kiến, không cam kết đạt được. Cắt lỗ áp dụng cho thời hạn và vùng giá vào của báo cáo; giá khớp thực tế có thể khác khi thị trường biến động.</p><p>Không mua cao hơn vùng giá mua. Nếu mở email muộn, hãy xem trạng thái mới nhất trước khi đặt lệnh.</p>${button(link(website,ticker))}`;
}
export function dailyBody(payload: Row, website: string): string {
  const opportunities = Array.isArray(payload.opportunities) ? payload.opportunities.filter((i: Row)=>i.publish_status==='PUBLISHED' && i.action==='MUA') : [];
  const changes = Array.isArray(payload.watchlist_changes) ? payload.watchlist_changes : [];
  const items = opportunities.map((i: Row)=>`<h2 style="font-size:18px">${esc(i.ticker)} · Mua</h2>` + table(
    row('Giá tham chiếu',price(i.reference_price)) + row('Vùng giá mua',range(i.buy_zone)) + pricePlanRows(i) + row('Xác nhận lúc',vietnamTime(i.confirmed_at))) + '<p>Mục tiêu là mức dự kiến; cắt lỗ áp dụng theo thời hạn và vùng giá vào của báo cáo. Không cam kết giá khớp hoặc lợi nhuận.</p>' + button(link(website,i.ticker,'daily_brief'))).join('');
  const changeRows = changes.map((i: Row)=>row(String(i.ticker),`${action(i.previous_state)} → ${action(i.current_state)}; ${vietnamTime(i.evaluated_at)}`)).join('');
  return `<div style="font-size:12px;font-weight:700;color:#64748b">BẢN TIN CỔ PHIẾU · ${esc(payload.report_date||vietnamTime(payload.generated_at))}</div><p>Phiên dữ liệu: ${esc(text(payload.market_session_reference||payload.as_of_date))}<br>Dữ liệu rà soát lúc ${esc(vietnamTime(payload.evaluated_at))}</p><h1 style="font-size:26px">${esc(payload.headline || (opportunities.length ? `${opportunities.length} mã được xác nhận mua` : 'Chưa có mã được xác nhận mua'))}</h1><p>Lập bản tin lúc ${esc(vietnamTime(payload.generated_at))}</p>` +
    (items || '<p>Chưa có khuyến nghị mua đủ điều kiện công bố trong lần rà soát này.</p>') +
    (changeRows ? `<h2 style="font-size:18px">Thay đổi trong danh sách của bạn</h2>${table(changeRows)}` : '') +
    `<p>Kiểm tra kế tiếp dự kiến: ${esc(vietnamTime(payload.next_review_at))}.</p>${button(link(website,undefined,'daily_brief'))}`;
}
