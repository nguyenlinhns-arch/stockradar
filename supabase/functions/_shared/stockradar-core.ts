export const STOCKRADAR_SYSTEM_CORE = `Bạn là StockRadar AI, trợ lý phân tích cổ phiếu HOSE dựa trên dữ liệu StockRadar.
Chỉ dùng số liệu trong RESEARCH_CONTEXT/ACTION_CONTEXT/USER_CONTEXT; không bịa giá, chỉ tiêu, vùng mua, stop, target hay xác suất. Dữ liệu StockRadar là nguồn chính.
Chỉ phân tích HOSE; không phân tích HNX, UPCoM, Crypto/Coin. Không tiết lộ mã ưu tiên nội bộ.
Áp dụng tư duy 4M/Payback, CANSLIM, định giá, SEPA/VCP/Stage, VPA/Pocket Pivot, Market Direction và quản trị rủi ro khi context có dữ liệu.
RESEARCH_ONLY: phân tích sâu nhưng các mức giá chỉ là tham chiếu nghiên cứu, chưa phải tín hiệu hành động.
REFERENCE_ONLY: dữ liệu hiện có nhưng mã chưa đạt research-ready; chỉ mô tả/tham chiếu, không khuyến nghị mua/bán.
METHOD_ONLY: chưa có snapshot đủ mới; không dùng dữ liệu cũ để suy đoán.
Trả lời tiếng Việt, quyết định trước. Một mã bắt đầu “KẾT LUẬN:”. Danh mục bắt đầu “VIỆC CẦN LÀM TRƯỚC:”. Không dùng Markdown **. Nếu dữ liệu thiếu thì nói rõ.`;

function o(v) { return v && typeof v === 'object' && !Array.isArray(v) ? v : {}; }
function n(v) { const x = Number(v); return Number.isFinite(x) ? x : null; }
function t(v) { return typeof v === 'string' ? v.trim() : v == null ? '' : String(v).trim(); }
function fn(v, d = 1) { const x = n(v); return x == null ? '' : x.toLocaleString('vi-VN', { maximumFractionDigits: d }); }
function fp(v) { const x = n(v); return x == null ? '' : `${Math.round(x).toLocaleString('vi-VN')}đ`; }
function pc(v, d = 1) { const x = n(v); return x == null ? '' : `${x.toLocaleString('vi-VN', { maximumFractionDigits: d })}%`; }
function up(p, x) { const a = n(p), b = n(x); return a && b != null ? (b / a - 1) * 100 : null; }
function state(v) {
  const s = t(v).replaceAll('_', ' ').replace(/\s+/g, ' ').trim();
  const m = { WATCH:'THEO DÕI', 'THEO DOI':'THEO DÕI', 'THEO DOI KHONG HANH DONG':'THEO DÕI — CHƯA HÀNH ĐỘNG', 'KHONG HANH DONG':'CHƯA HÀNH ĐỘNG', 'HA TY TRONG HOAC BAN':'HẠ TỶ TRỌNG HOẶC BÁN', GIU:'GIỮ', 'PHAN HOA THAN TRONG':'PHÂN HÓA, THẬN TRỌNG', LAGGING:'YẾU HƠN THỊ TRƯỜNG', LEADING:'DẪN DẮT', 'RESEARCH READY WATCH':'THEO DÕI — DỮ LIỆU NGHIÊN CỨU SẴN SÀNG' };
  return m[s.toUpperCase()] || s;
}
const RM = { NO_BUY_SETUP:'chưa có setup mua đạt chuẩn', MISSING_ACTION_MAP:'chưa có bản đồ hành động đã xác nhận', UPSIDE_TOO_LOW:'dư địa tăng tại điểm vào hiện tại chưa đủ hấp dẫn', RR_BELOW_2:'Risk/Reward dưới 2', CURRENT_CORPORATE_ACTION_UNVERIFIED:'cần kiểm tra thêm sự kiện/quyền doanh nghiệp hiện tại' };
function reasons(v) { return (Array.isArray(v) ? v : t(v).split('|')).map(t).filter(Boolean).map(x => RM[x] || state(x)).join('; '); }
function intent(q) {
  const s = t(q).toLowerCase();
  if (/(rủi ro|rui ro|nguy cơ|cắt lỗ|cat lo)/.test(s)) return 'RISK';
  if (/(3\s*[-–]?\s*6|trung hạn|trung han|6 tháng|6 thang)/.test(s)) return 'MEDIUM';
  if (/(12\s*tháng|12\s*thang|dài hạn|dai han|tích sản|tich san)/.test(s)) return 'LONG';
  if (/(đang nắm|dang nam|đang giữ|dang giu|giá vốn|gia von|bán không|ban khong)/.test(s)) return 'HOLD';
  if (/(catalyst|tin tức|tin tuc|sự kiện|su kien)/.test(s)) return 'CATALYST';
  if (/(định giá|dinh gia|fair value|p\/e|p\/b)/.test(s)) return 'VALUE';
  return 'BUY';
}

export function stockRadarMode(actionReady, researchReady, referenceReady = false) {
  if (actionReady) return 'ACTION_READY';
  if (researchReady) return 'RESEARCH_ONLY';
  if (referenceReady) return 'REFERENCE_ONLY';
  return 'METHOD_ONLY';
}

export function normalizeResearchContext(raw) {
  if (!raw || !['INTERNAL_RESEARCH_READY','INTERNAL_REFERENCE_READY'].includes(raw.status)) return null;
  const p = o(raw.payload);
  return {
    status:'CONTEXT_READY', context_grade:raw.context_grade || (raw.status === 'INTERNAL_RESEARCH_READY' ? 'RESEARCH_READY' : 'REFERENCE_ONLY'),
    ticker:raw.ticker, snapshot_id:raw.snapshot_id, generated_at:raw.generated_at, as_of_date:raw.as_of_date, price_snapshot_status:raw.price_snapshot_status,
    company_type:p.company_type, sector:p.sector, business_bucket:p.business_bucket,
    quote:o(p.quote), setup:o(p.setup), scores:o(p.scores), risk:o(p.risk), market_context:o(p.market_context), trade_plan:o(p.trade_plan), fundamental_valuation:o(p.fundamental_valuation), catalyst:o(p.catalyst), corporate_action:o(p.corporate_action), supply_institutional:o(p.supply_institutional), release:o(p.release), research_v7:o(p.research_v7)
  };
}

function one(c, q, reference = false) {
  const tick=t(c.ticker), quote=o(c.quote), s=o(c.setup), sc=o(c.scores), r=o(c.risk), m=o(c.market_context), p=o(c.trade_plan), cat=o(c.catalyst), ca=o(c.corporate_action), sup=o(c.supply_institutional);
  const price=n(quote.price) ?? n(o(c.research_v7).price), setup=state(s.candidate_setup || o(c.research_v7).candidate_setup), ns=state(s.new_position_state_v5 || o(c.research_v7).new_position_state_v5), hs=state(s.holding_state_v5 || o(c.research_v7).holding_state_v5), it=intent(q);
  const wait=!setup || setup.includes('THEO DÕI') || ns.includes('THEO DÕI') || ns.includes('CHƯA HÀNH ĐỘNG');
  const lines=[reference ? `KẾT LUẬN: ${tick} có dữ liệu tham chiếu nhưng CHƯA ĐẠT research-ready; chưa dùng để quyết định mua/bán.` : (wait ? `KẾT LUẬN: ${tick} CHƯA MUA MỚI. Tiếp tục theo dõi và chờ setup/dòng tiền xác nhận.` : `KẾT LUẬN: ${tick} có setup ${setup}, nhưng chưa coi là tín hiệu hành động đã xác nhận.`)];
  const why=[]; if(price!=null) why.push(`giá ${fp(price)}`); if(setup) why.push(`setup ${setup}`);
  for (const [label,v] of [['Radar',sc.radar_score_v7],['cơ bản',sc.fundamental_domain_score_v4],['kỹ thuật',sc.technical_score],['dòng tiền',sc.flow_score_v4],['định giá',sc.valuation_domain_score_v4],['sức mạnh ngành',sc.sector_strength_score],['thị trường',sc.market_score],['cung/cầu',sc.supply_demand_score_v1],['thanh khoản',sc.liquidity_score_v4]]) if(n(v)!=null) why.push(`${label} ${fn(v,1)}/100`);
  const mr=state(m.market_regime), sr=state(m.sector_regime); if(mr) why.push(`bối cảnh ${mr}`); if(sr) why.push(`ngành ${sr}`);
  const risk=[]; const br=reasons(r.decision_block_reasons_v5); if(br) risk.push(br); if(n(r.atr20_pct)!=null) risk.push(`ATR20 ${pc(r.atr20_pct)}`); if(n(r.realized_vol20_pct)!=null) risk.push(`biến động 20 phiên ${pc(r.realized_vol20_pct)}`); if(n(r.max_drawdown60_pct)!=null) risk.push(`drawdown 60 phiên ${pc(r.max_drawdown60_pct)}`); if(ca.review_required_v2===true) risk.push('corporate action cần rà soát');
  const refs=[]; for(const [label,v] of [['3–6 tháng',p.target_3_6m],['12 tháng',p.target_12m]]) if(n(v)!=null){ const u=up(price,v); refs.push(`${label} ${fp(v)}${u!=null?` (${u>=0?'+':''}${pc(u)})`:''}`); }
  const ct=t(cat.latest_official_title_v3), tm=t(cat.latest_official_time_v3);
  if(it==='HOLD'){ if(hs) lines.push(`NẾU ĐANG NẮM GIỮ: trạng thái nghiên cứu ${hs}.`); if(risk.length) lines.push(`RỦI RO / ĐIỀU KIỆN ĐỔI: ${risk.join('; ')}.`); }
  else if(it==='RISK'){ if(risk.length) lines.push(`RỦI RO / ĐIỀU KIỆN ĐỔI: ${risk.join('; ')}.`); if(why.length) lines.push(`BỐI CẢNH: ${why.join(' · ')}.`); }
  else if(it==='CATALYST'){ lines.push(ct ? `CATALYST: ${ct}${tm?` (${tm})`:''}.` : 'CATALYST: snapshot hiện chưa có sự kiện chính thức đủ rõ để nêu.'); if(risk.length) lines.push(`RỦI RO: ${risk.join('; ')}.`); }
  else if(it==='MEDIUM'||it==='LONG'||it==='VALUE'){ if(refs.length) lines.push(`${reference?'THAM CHIẾU SƠ BỘ':'THAM CHIẾU NGHIÊN CỨU'}: ${refs.join(' · ')}.`); if(why.length) lines.push(`VÌ SAO: ${why.join(' · ')}.`); if(risk.length) lines.push(`RỦI RO: ${risk.join('; ')}.`); }
  else { if(ns) lines.push(`MUA MỚI: trạng thái nghiên cứu ${ns}.`); if(why.length) lines.push(`VÌ SAO: ${why.join(' · ')}.`); if(refs.length&&!reference) lines.push(`THAM CHIẾU NGHIÊN CỨU: ${refs.join(' · ')}.`); if(risk.length) lines.push(`RỦI RO / ĐIỀU KIỆN ĐỔI: ${risk.join('; ')}.`); }
  if(ct && it!=='CATALYST') lines.push(`CATALYST: ${ct}${tm?` (${tm})`:''}.`);
  const extra=[]; if(n(sup.free_float_proxy_pct)!=null) extra.push(`free-float proxy ${pc(sup.free_float_proxy_pct)}`); if(n(sup.float_turnover20_pct)!=null) extra.push(`turnover20 ${pc(sup.float_turnover20_pct,2)}`); if(extra.length && ['BUY','RISK'].includes(it)) lines.push(`CUNG / TỔ CHỨC: ${extra.join(' · ')}.`);
  lines.push(`DỮ LIỆU: ${t(c.as_of_date)||t(c.generated_at)}.`);
  lines.push(reference ? 'Dữ liệu tham chiếu — mã chưa đạt research-ready, không dùng như tín hiệu hành động.' : 'Góc nhìn nghiên cứu — chưa phải tín hiệu hành động đã được xác nhận.');
  return lines.join('\n\n');
}

export function deterministicStockRadarAnswer({ mode, researchContext, actionContext, question='' }) {
  const list=Array.isArray(researchContext)?researchContext.filter(Boolean):researchContext?[researchContext]:[];
  if(mode==='RESEARCH_ONLY' && list.length===1) return one(list[0],question,false);
  if(mode==='REFERENCE_ONLY' && list.length===1) return one(list[0],question,true);
  if((mode==='RESEARCH_ONLY'||mode==='REFERENCE_ONLY') && list.length>1){
    const rows=list.slice(0,20).map(c=>{const p=n(o(c.quote).price),s=state(o(c.setup).candidate_setup),r=n(o(c.scores).radar_score_v7),g=t(c.context_grade)==='RESEARCH_READY'?'READY':'REF';return `- ${t(c.ticker)}: ${p!=null?fp(p):'chưa có giá'}${s?` · ${s}`:''}${r!=null?` · Radar ${fn(r,1)}`:''} · ${g}`;});
    return `VIỆC CẦN LÀM TRƯỚC: ưu tiên mã READY có setup rõ và ít điểm chặn hơn.\n\n${rows.join('\n')}\n\nMã REF chỉ là dữ liệu tham chiếu, không dùng như tín hiệu hành động.`;
  }
  if(mode==='ACTION_READY' && Array.isArray(actionContext) && actionContext.length) return 'KẾT LUẬN: có Action Report đã xác nhận; chỉ dùng đúng các mức đã phát hành.';
  return 'KẾT LUẬN: chưa có snapshot đủ mới cho mã này. StockRadar AI không dùng giá hoặc tín hiệu cũ để suy đoán.';
}
