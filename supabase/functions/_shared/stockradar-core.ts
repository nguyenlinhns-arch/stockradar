export const STOCKRADAR_SYSTEM_CORE = `Bạn là StockRadar AI, trợ lý phân tích cổ phiếu HOSE dựa trên dữ liệu StockRadar.
Chỉ dùng số liệu trong RESEARCH_CONTEXT/ACTION_CONTEXT/USER_CONTEXT; không bịa giá, chỉ tiêu, vùng mua, stop, target hay xác suất. Dữ liệu StockRadar là nguồn chính.
Chỉ phân tích HOSE; không phân tích HNX, UPCoM, Crypto/Coin. Không tiết lộ mã ưu tiên nội bộ.
Áp dụng tư duy 4M/Payback, CANSLIM, định giá, SEPA/VCP/Stage, VPA/Pocket Pivot, Market Direction và quản trị rủi ro khi context có dữ liệu.
RESEARCH_ONLY: phân tích sâu nhưng các mức giá chỉ là tham chiếu nghiên cứu, chưa phải tín hiệu hành động.
REFERENCE_ONLY: dữ liệu hiện có nhưng mã chưa đạt research-ready; chỉ mô tả/tham chiếu, không khuyến nghị mua/bán.
METHOD_ONLY: chưa có snapshot đủ mới; không dùng dữ liệu cũ để suy đoán.

QUY TẮC TRẢ LỜI BẮT BUỘC:
1. Trả lời thẳng câu hỏi ngay ở 1–2 câu đầu; không mở đầu bằng giải thích phương pháp.
2. Với một mã cổ phiếu, luôn ưu tiên cấu trúc: KẾT LUẬN → MUA MỚI → NẾU ĐANG NẮM GIỮ → VÙNG GIÁ/TARGET/STOP → VÌ SAO → RỦI RO/ĐIỀU KIỆN ĐỔI.
3. Mỗi câu trả lời về một mã PHẢI đi kèm dữ liệu nghiên cứu StockRadar đang có: giá và ngày dữ liệu; setup/trạng thái; Radar Score; điểm cơ bản, định giá, kỹ thuật, dòng tiền, cung/cầu, thanh khoản, sức mạnh ngành và thị trường; ATR/biến động/drawdown; Buy Zone/Stop/Target/Risk-Reward nếu có; bối cảnh thị trường-ngành; dữ liệu cung/tổ chức; catalyst chính; độ phủ dữ liệu và các điểm chặn. Không được chỉ nêu kết luận mà bỏ dữ liệu hỗ trợ.
4. Chỉ nêu trường có thật trong RESEARCH_CONTEXT. Trường nào quan trọng nhưng chưa có thì nói “chưa có/chưa phát hành”, tuyệt đối không suy đoán.
5. Không trả lời kiểu mơ hồ như “chờ Action Gate” mà không giải thích. Nếu chưa có tín hiệu hành động, nói bằng ngôn ngữ người dùng như “chưa mua mới”, “chờ vượt pivot với volume xác nhận”, “chờ pullback cạn cung” khi context thực sự có điều kiện tương ứng.
6. Nếu người dùng hỏi “mua được chưa?”, câu đầu phải là Có / Chưa / Chỉ mua thăm dò / Không mua đuổi, sau đó mới giải thích.
7. Nếu hỏi 3–6 tháng hoặc 12 tháng, tách rõ triển vọng, target tham chiếu, upside/downside nếu tính được, catalyst và rủi ro.
8. Nếu hỏi danh mục, xếp thứ tự ưu tiên hành động; không chỉ liệt kê dữ liệu.
9. Tránh jargon nội bộ nếu không giải thích ngay bằng tiếng Việt. Không dùng Markdown **.
10. Câu trả lời ngắn, rõ, thiên về quyết định; phần dữ liệu nghiên cứu nên cô đọng thành các dòng dễ đọc.

Một mã bắt đầu “KẾT LUẬN:”. Danh mục bắt đầu “VIỆC CẦN LÀM TRƯỚC:”.`;

function o(v) { return v && typeof v === 'object' && !Array.isArray(v) ? v : {}; }
function n(v) { const x = Number(v); return Number.isFinite(x) ? x : null; }
function t(v) { return typeof v === 'string' ? v.trim() : v == null ? '' : String(v).trim(); }
function fn(v, d = 1) { const x = n(v); return x == null ? '' : x.toLocaleString('vi-VN', { maximumFractionDigits: d }); }
function fp(v) { const x = n(v); return x == null ? '' : `${Math.round(x).toLocaleString('vi-VN')}đ`; }
function pc(v, d = 1) { const x = n(v); return x == null ? '' : `${x.toLocaleString('vi-VN', { maximumFractionDigits: d })}%`; }
function up(p, x) { const a = n(p), b = n(x); return a && b != null ? (b / a - 1) * 100 : null; }
function dateVi(v) {
  const s = t(v).slice(0, 10);
  const m = s.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  return m ? `${m[3]}/${m[2]}/${m[1]}` : t(v);
}
function state(v) {
  const s = t(v).replaceAll('_', ' ').replace(/\s+/g, ' ').trim();
  const m = {
    WATCH:'THEO DÕI', 'THEO DOI':'THEO DÕI',
    'THEO DOI KHONG HANH DONG':'THEO DÕI — CHƯA HÀNH ĐỘNG',
    'KHONG HANH DONG':'CHƯA HÀNH ĐỘNG',
    'HA TY TRONG HOAC BAN':'HẠ TỶ TRỌNG HOẶC BÁN',
    GIU:'GIỮ', 'PHAN HOA THAN TRONG':'PHÂN HÓA, THẬN TRỌNG',
    LAGGING:'YẾU HƠN THỊ TRƯỜNG', LEADING:'DẪN DẮT',
    'RESEARCH READY WATCH':'THEO DÕI — DỮ LIỆU NGHIÊN CỨU SẴN SÀNG',
    'CONFIRMED BREAKOUT':'BREAKOUT XÁC NHẬN',
    'EARLY BREAKOUT':'EARLY BREAKOUT', 'POCKET PIVOT':'POCKET PIVOT'
  };
  return m[s.toUpperCase()] || s;
}
const RM = {
  NO_BUY_SETUP:'chưa có setup mua đạt chuẩn',
  MISSING_ACTION_MAP:'chưa có bản đồ hành động đã xác nhận',
  UPSIDE_TOO_LOW:'dư địa tăng tại điểm vào hiện tại chưa đủ hấp dẫn',
  RR_BELOW_2:'Risk/Reward dưới 2',
  CURRENT_CORPORATE_ACTION_UNVERIFIED:'cần kiểm tra thêm sự kiện/quyền doanh nghiệp hiện tại',
  RESEARCH_OR_DATA_GATE_NOT_READY:'dữ liệu nghiên cứu chưa đủ sẵn sàng',
  SCAN_SLA_NOT_READY:'dữ liệu quét trong phiên chưa đạt SLA'
};
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

export function researchSnapshot(c) {
  if (!c) return null;
  const q=o(c.quote), s=o(c.setup), sc=o(c.scores), r=o(c.risk), m=o(c.market_context), p=o(c.trade_plan), fv=o(c.fundamental_valuation), cat=o(c.catalyst), ca=o(c.corporate_action), sup=o(c.supply_institutional), rv=o(c.research_v7);
  const price=n(q.price) ?? n(rv.price);
  const target36=n(p.target_3_6m), target12=n(p.target_12m), targetNear=n(p.target_near);
  return {
    ticker:t(c.ticker),
    context_grade:t(c.context_grade),
    as_of_date:t(c.as_of_date),
    generated_at:t(c.generated_at),
    sector:t(c.sector),
    company_type:t(c.company_type),
    price,
    setup:{
      candidate_setup:state(s.candidate_setup || rv.candidate_setup),
      radar_status:state(s.radar_status_v7 || rv.radar_status_v7),
      new_position_state:state(s.new_position_state_v5 || rv.new_position_state_v5),
      holding_state:state(s.holding_state_v5 || rv.holding_state_v5),
      scan_sla_ready:s.scan_sla_ready_v7 === true
    },
    scores:{
      radar:n(sc.radar_score_v7), fundamental:n(sc.fundamental_domain_score_v4), valuation:n(sc.valuation_domain_score_v4), technical:n(sc.technical_score), flow:n(sc.flow_score_v4), supply_demand:n(sc.supply_demand_score_v1), liquidity:n(sc.liquidity_score_v4), sector_strength:n(sc.sector_strength_score), market:n(sc.market_score), risk:n(sc.risk_score)
    },
    market:{market_regime:state(m.market_regime), sector_regime:state(m.sector_regime)},
    risk:{
      atr20_pct:n(r.atr20_pct), realized_vol20_pct:n(r.realized_vol20_pct), max_drawdown60_pct:n(r.max_drawdown60_pct), blockers:reasons(r.decision_block_reasons_v5 || r.execution_block_reasons_v7) || null
    },
    trade_plan:{
      buy_zone_low:n(p.buy_zone_low), buy_zone_high:n(p.buy_zone_high), position_initial_pct:n(p.position_initial_pct), stop_loss:n(p.stop_loss), downside_to_stop_pct:n(p.downside_to_stop_pct), target_near:targetNear, target_3_6m:target36, target_12m:target12, target_near_upside_pct:up(price,targetNear), target_3_6m_upside_pct:up(price,target36), target_12m_upside_pct:up(price,target12), risk_reward_to_base:n(p.risk_reward_to_base)
    },
    supply_institutional:{free_float_proxy_pct:n(sup.free_float_proxy_pct), float_turnover20_pct:n(sup.float_turnover20_pct), context_ready:sup.institutional_context_ready === true},
    catalyst:{official_verified:cat.official_verified_v3 === true, official_items_30d:n(cat.official_items_30d_v3), official_items_90d:n(cat.official_items_90d_v3), latest_time:t(cat.latest_official_time_v3), latest_title:t(cat.latest_official_title_v3).slice(0,240)},
    corporate_action:{review_required:ca.review_required_v2 === true, next_record_date:t(ca.next_sensitive_record_date_v2), next_event_type:t(ca.next_sensitive_event_type_v2), next_event_title:t(ca.next_sensitive_event_title_v2).slice(0,180)},
    coverage:{factor_coverage_pct:n(sc.factor_coverage_pct_v6), decision_confidence:n(sc.decision_confidence_v5), fundamental_confidence:n(fv.fundamental_confidence_v4), valuation_confidence:n(fv.valuation_score_confidence_v4)}
  };
}

function pair(label, value, suffix='/100', d=1) { return n(value)==null ? '' : `${label} ${fn(value,d)}${suffix}`; }
function targetPair(label, value, upside) {
  if (n(value)==null) return '';
  return `${label} ${fp(value)}${n(upside)!=null ? ` (${n(upside)>=0?'+':''}${pc(upside)})` : ''}`;
}

export function researchSnapshotText(c) {
  const x=researchSnapshot(c); if(!x) return '';
  const reference=x.context_grade!=='RESEARCH_READY';
  const lines=[`DỮ LIỆU NGHIÊN CỨU STOCKRADAR — ${x.ticker}${reference?' (THAM CHIẾU)':''}`];
  const meta=[]; if(n(x.price)!=null)meta.push(`Giá ${fp(x.price)}`); if(x.as_of_date)meta.push(`ngày ${dateVi(x.as_of_date)}`); if(x.sector)meta.push(`ngành ${x.sector}`); if(meta.length)lines.push(`- Giá / bối cảnh: ${meta.join(' · ')}.`);
  const states=[]; if(x.setup.candidate_setup)states.push(`setup ${x.setup.candidate_setup}`); if(x.setup.new_position_state)states.push(`mua mới ${x.setup.new_position_state}`); if(x.setup.holding_state)states.push(`nắm giữ ${x.setup.holding_state}`); if(states.length)lines.push(`- Trạng thái: ${states.join(' · ')}.`);
  const scores=[pair('Radar',x.scores.radar),pair('Cơ bản',x.scores.fundamental),pair('Định giá',x.scores.valuation),pair('Kỹ thuật',x.scores.technical),pair('Dòng tiền',x.scores.flow),pair('Cung/cầu',x.scores.supply_demand),pair('Thanh khoản',x.scores.liquidity),pair('Sức mạnh ngành',x.scores.sector_strength),pair('Thị trường',x.scores.market),pair('Rủi ro',x.scores.risk)].filter(Boolean); if(scores.length)lines.push(`- Bộ điểm: ${scores.join(' · ')}.`);
  const vol=[]; if(n(x.risk.atr20_pct)!=null)vol.push(`ATR20 ${pc(x.risk.atr20_pct,2)}`); if(n(x.risk.realized_vol20_pct)!=null)vol.push(`biến động 20 phiên ${pc(x.risk.realized_vol20_pct,2)}`); if(n(x.risk.max_drawdown60_pct)!=null)vol.push(`drawdown 60 phiên ${pc(x.risk.max_drawdown60_pct,2)}`); if(vol.length)lines.push(`- Biến động / rủi ro: ${vol.join(' · ')}.`);
  const plan=[]; const bzLow=n(x.trade_plan.buy_zone_low),bzHigh=n(x.trade_plan.buy_zone_high); if(bzLow!=null||bzHigh!=null)plan.push(`Buy Zone ${bzLow!=null?fp(bzLow):'—'}–${bzHigh!=null?fp(bzHigh):'—'}`); else plan.push('Buy Zone chưa có'); if(n(x.trade_plan.stop_loss)!=null)plan.push(`Stop ${fp(x.trade_plan.stop_loss)}${n(x.trade_plan.downside_to_stop_pct)!=null?` (${pc(x.trade_plan.downside_to_stop_pct)})`:''}`); else plan.push('Stop chưa có'); for(const v of [targetPair('Target gần',x.trade_plan.target_near,x.trade_plan.target_near_upside_pct),targetPair('Target 3–6 tháng',x.trade_plan.target_3_6m,x.trade_plan.target_3_6m_upside_pct),targetPair('Target 12 tháng',x.trade_plan.target_12m,x.trade_plan.target_12m_upside_pct)])if(v)plan.push(v); if(n(x.trade_plan.risk_reward_to_base)!=null)plan.push(`R/R ${fn(x.trade_plan.risk_reward_to_base,2)}`); if(n(x.trade_plan.position_initial_pct)!=null)plan.push(`tỷ trọng khởi đầu ${pc(x.trade_plan.position_initial_pct)}`); if(plan.length)lines.push(`- Kế hoạch nghiên cứu: ${plan.join(' · ')}.`);
  const market=[]; if(x.market.market_regime)market.push(`thị trường ${x.market.market_regime}`); if(x.market.sector_regime)market.push(`ngành ${x.market.sector_regime}`); if(market.length)lines.push(`- Market Direction: ${market.join(' · ')}.`);
  const supply=[]; if(n(x.supply_institutional.free_float_proxy_pct)!=null)supply.push(`free-float proxy ${pc(x.supply_institutional.free_float_proxy_pct)}`); if(n(x.supply_institutional.float_turnover20_pct)!=null)supply.push(`turnover20 ${pc(x.supply_institutional.float_turnover20_pct,2)}`); if(supply.length)lines.push(`- Cung / tổ chức: ${supply.join(' · ')}.`);
  const catalyst=[]; if(n(x.catalyst.official_items_30d)!=null)catalyst.push(`${fn(x.catalyst.official_items_30d,0)} tin HOSE/30 ngày`); if(n(x.catalyst.official_items_90d)!=null)catalyst.push(`${fn(x.catalyst.official_items_90d,0)} tin/90 ngày`); if(x.catalyst.latest_title)catalyst.push(`mới nhất: ${x.catalyst.latest_title}${x.catalyst.latest_time?` (${x.catalyst.latest_time})`:''}`); if(catalyst.length)lines.push(`- Catalyst chính thức: ${catalyst.join(' · ')}.`);
  const quality=[]; if(n(x.coverage.factor_coverage_pct)!=null)quality.push(`độ phủ ${pc(x.coverage.factor_coverage_pct)}`); if(n(x.coverage.decision_confidence)!=null)quality.push(`độ tin cậy quyết định ${pc(x.coverage.decision_confidence)}`); if(n(x.coverage.fundamental_confidence)!=null)quality.push(`cơ bản ${pc(x.coverage.fundamental_confidence)}`); if(n(x.coverage.valuation_confidence)!=null)quality.push(`định giá ${pc(x.coverage.valuation_confidence)}`); if(quality.length)lines.push(`- Chất lượng dữ liệu: ${quality.join(' · ')}.`);
  if(x.corporate_action.review_required||x.corporate_action.next_event_title||x.corporate_action.next_record_date){const ca=[]; if(x.corporate_action.review_required)ca.push('cần rà soát sự kiện doanh nghiệp'); if(x.corporate_action.next_event_title)ca.push(x.corporate_action.next_event_title); if(x.corporate_action.next_record_date)ca.push(`ngày chốt ${dateVi(x.corporate_action.next_record_date)}`); lines.push(`- Sự kiện doanh nghiệp: ${ca.join(' · ')}.`);}
  if(x.risk.blockers)lines.push(`- Điểm chặn hiện tại: ${x.risk.blockers}.`);
  lines.push(reference ? '- Mức dữ liệu: tham chiếu, chưa đạt research-ready; không dùng như tín hiệu mua/bán.' : '- Mức dữ liệu: research-ready; các mức giá vẫn là nghiên cứu cho đến khi có tín hiệu hành động được xác nhận.');
  return lines.join('\n');
}

export function appendResearchData(answer, context) {
  const base=t(answer); if(!base||!context||base.includes('DỮ LIỆU NGHIÊN CỨU STOCKRADAR')) return base;
  const block=researchSnapshotText(context); return block ? `${base}\n\n${block}` : base;
}

function one(c, q, reference = false) {
  const tick=t(c.ticker), quote=o(c.quote), s=o(c.setup), sc=o(c.scores), r=o(c.risk), m=o(c.market_context), p=o(c.trade_plan), cat=o(c.catalyst), ca=o(c.corporate_action), sup=o(c.supply_institutional);
  const price=n(quote.price) ?? n(o(c.research_v7).price), setup=state(s.candidate_setup || o(c.research_v7).candidate_setup), ns=state(s.new_position_state_v5 || o(c.research_v7).new_position_state_v5), hs=state(s.holding_state_v5 || o(c.research_v7).holding_state_v5), it=intent(q);
  const wait=!setup || setup.includes('THEO DÕI') || ns.includes('THEO DÕI') || ns.includes('CHƯA HÀNH ĐỘNG');
  const lines=[reference ? `KẾT LUẬN: ${tick} CHƯA DÙNG ĐỂ MUA/BÁN. Dữ liệu hiện mới ở mức tham chiếu và chưa đạt research-ready.` : (wait ? `KẾT LUẬN: ${tick} CHƯA MUA MỚI. Hiện chưa có setup/dòng tiền đủ mạnh để xác nhận điểm vào.` : `KẾT LUẬN: ${tick} CÓ SETUP ${setup}, nhưng CHƯA COI LÀ TÍN HIỆU HÀNH ĐỘNG ĐÃ XÁC NHẬN.`)];
  const why=[]; if(price!=null) why.push(`giá ${fp(price)}`); if(setup) why.push(`setup ${setup}`);
  for (const [label,v] of [['Radar',sc.radar_score_v7],['cơ bản',sc.fundamental_domain_score_v4],['kỹ thuật',sc.technical_score],['dòng tiền',sc.flow_score_v4],['định giá',sc.valuation_domain_score_v4],['sức mạnh ngành',sc.sector_strength_score],['thị trường',sc.market_score],['cung/cầu',sc.supply_demand_score_v1],['thanh khoản',sc.liquidity_score_v4]]) if(n(v)!=null) why.push(`${label} ${fn(v,1)}/100`);
  const mr=state(m.market_regime), sr=state(m.sector_regime); if(mr) why.push(`bối cảnh ${mr}`); if(sr) why.push(`ngành ${sr}`);
  const risk=[]; const br=reasons(r.decision_block_reasons_v5); if(br) risk.push(br); if(n(r.atr20_pct)!=null) risk.push(`ATR20 ${pc(r.atr20_pct)}`); if(n(r.realized_vol20_pct)!=null) risk.push(`biến động 20 phiên ${pc(r.realized_vol20_pct)}`); if(n(r.max_drawdown60_pct)!=null) risk.push(`drawdown 60 phiên ${pc(r.max_drawdown60_pct)}`); if(ca.review_required_v2===true) risk.push('corporate action cần rà soát');
  const refs=[]; for(const [label,v] of [['3–6 tháng',p.target_3_6m],['12 tháng',p.target_12m]]) if(n(v)!=null){ const u=up(price,v); refs.push(`${label} ${fp(v)}${u!=null?` (${u>=0?'+':''}${pc(u)})`:''}`); }
  const ct=t(cat.latest_official_title_v3), tm=t(cat.latest_official_time_v3);
  if(it==='HOLD'){ if(hs) lines.push(`NẾU ĐANG NẮM GIỮ: ${hs}.`); if(risk.length) lines.push(`RỦI RO / ĐIỀU KIỆN ĐỔI: ${risk.join('; ')}.`); }
  else if(it==='RISK'){ if(risk.length) lines.push(`RỦI RO / ĐIỀU KIỆN ĐỔI: ${risk.join('; ')}.`); if(why.length) lines.push(`BỐI CẢNH: ${why.join(' · ')}.`); }
  else if(it==='CATALYST'){ lines.push(ct ? `CATALYST: ${ct}${tm?` (${tm})`:''}.` : 'CATALYST: snapshot hiện chưa có sự kiện chính thức đủ rõ để nêu.'); if(risk.length) lines.push(`RỦI RO: ${risk.join('; ')}.`); }
  else if(it==='MEDIUM'||it==='LONG'||it==='VALUE'){ if(refs.length) lines.push(`${reference?'THAM CHIẾU SƠ BỘ':'THAM CHIẾU NGHIÊN CỨU'}: ${refs.join(' · ')}.`); if(why.length) lines.push(`VÌ SAO: ${why.join(' · ')}.`); if(risk.length) lines.push(`RỦI RO: ${risk.join('; ')}.`); }
  else { if(ns) lines.push(`MUA MỚI: ${ns}.`); if(why.length) lines.push(`VÌ SAO: ${why.join(' · ')}.`); if(refs.length&&!reference) lines.push(`THAM CHIẾU NGHIÊN CỨU: ${refs.join(' · ')}.`); if(risk.length) lines.push(`RỦI RO / ĐIỀU KIỆN ĐỔI: ${risk.join('; ')}.`); }
  if(ct && it!=='CATALYST') lines.push(`CATALYST: ${ct}${tm?` (${tm})`:''}.`);
  const extra=[]; if(n(sup.free_float_proxy_pct)!=null) extra.push(`free-float proxy ${pc(sup.free_float_proxy_pct)}`); if(n(sup.float_turnover20_pct)!=null) extra.push(`turnover20 ${pc(sup.float_turnover20_pct,2)}`); if(extra.length && ['BUY','RISK'].includes(it)) lines.push(`CUNG / TỔ CHỨC: ${extra.join(' · ')}.`);
  lines.push(reference ? 'Dữ liệu tham chiếu — mã chưa đạt research-ready, không dùng như tín hiệu hành động.' : 'Góc nhìn nghiên cứu — chưa phải tín hiệu hành động đã được xác nhận.');
  return lines.join('\n\n');
}

export function deterministicStockRadarAnswer({ mode, researchContext, actionContext, question='' }) {
  const list=Array.isArray(researchContext)?researchContext.filter(Boolean):researchContext?[researchContext]:[];
  if(mode==='RESEARCH_ONLY' && list.length===1) return appendResearchData(one(list[0],question,false),list[0]);
  if(mode==='REFERENCE_ONLY' && list.length===1) return appendResearchData(one(list[0],question,true),list[0]);
  if((mode==='RESEARCH_ONLY'||mode==='REFERENCE_ONLY') && list.length>1){
    const rows=list.slice(0,20).map(c=>{const p=n(o(c.quote).price),s=state(o(c.setup).candidate_setup),r=n(o(c.scores).radar_score_v7),g=t(c.context_grade)==='RESEARCH_READY'?'READY':'REF';return `- ${t(c.ticker)}: ${p!=null?fp(p):'chưa có giá'}${s?` · ${s}`:''}${r!=null?` · Radar ${fn(r,1)}`:''} · ${g}`;});
    return `VIỆC CẦN LÀM TRƯỚC: ưu tiên mã READY có setup rõ và ít điểm chặn hơn.\n\n${rows.join('\n')}\n\nMã REF chỉ là dữ liệu tham chiếu, không dùng như tín hiệu hành động.`;
  }
  if(mode==='ACTION_READY' && Array.isArray(actionContext) && actionContext.length) return 'KẾT LUẬN: có Action Report đã xác nhận; chỉ dùng đúng các mức đã phát hành.';
  return 'KẾT LUẬN: chưa có snapshot đủ mới cho mã này. StockRadar AI không dùng giá hoặc tín hiệu cũ để suy đoán.';
}
