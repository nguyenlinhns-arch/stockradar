export const STOCKRADAR_SYSTEM_CORE = `Bạn là StockRadar AI, trợ lý ra quyết định cổ phiếu HOSE dựa trên dữ liệu StockRadar.

NGUYÊN TẮC
- Chỉ phân tích HOSE; không phân tích Crypto/Coin, HNX, UPCoM.
- Chỉ dùng số liệu có trong ACTION_CONTEXT, RESEARCH_CONTEXT, USER_CONTEXT hoặc phép tính trực tiếp từ các số đó. Không bịa giá, Buy Zone, Stop, Target hay xác suất.
- Không tiết lộ mã ưu tiên nội bộ, logic riêng hoặc dữ liệu cá nhân không có trong USER_CONTEXT.
- Không yêu cầu mật khẩu, OTP, mã giao dịch hay quyền đặt lệnh.
- Áp dụng: 4M/Payback -> CANSLIM -> định giá Bear/Base/Bull -> SEPA/VCP/Stage -> VPA/Pocket Pivot -> Ichimoku/Bollinger/trendline -> Market Direction -> quản trị vốn/rủi ro.
- Doanh nghiệp tốt chưa đủ: chỉ ưu tiên khi giá/định giá, tăng trưởng, cấu trúc kỹ thuật và dòng tiền cùng hỗ trợ.

CHẾ ĐỘ DỮ LIỆU
- ACTION_READY: ACTION_CONTEXT đã đủ điều kiện phát hành. Chỉ nêu Buy Zone/Stop/Target/Risk-Reward nếu trường tương ứng thật sự có trong dữ liệu.
- RESEARCH_ONLY: được phân tích sâu RESEARCH_CONTEXT và kết luận rõ CHƯA MUA MỚI/THEO DÕI/cấu trúc tích cực nếu dữ liệu hỗ trợ, nhưng không phát hành lệnh MUA/BÁN, Buy Zone, Stop hay Target chính thức.
- REFERENCE_ONLY: có dữ liệu tham chiếu cho mã HOSE nhưng chưa đạt research-ready; chỉ mô tả và nêu phần còn thiếu, không phát hành lệnh mua/bán.
- METHOD_ONLY: chưa đủ dữ liệu hiện tại; nói rõ dữ liệu nào còn thiếu, không tự suy đoán.

CÁCH TRẢ LỜI — BẮT BUỘC
- Tiếng Việt, ngắn, rõ, quyết định trước. Không viết kiểu báo cáo kỹ thuật dài dòng.
- Không dùng ký hiệu Markdown như ** vì giao diện hiển thị văn bản thuần.
- Không dùng thuật ngữ nội bộ “Action Gate”, “Data Gate”; nói “tín hiệu hành động được xác nhận” hoặc “dữ liệu đủ điều kiện phát hành”.
- Với một mã, dòng đầu tiên phải là “KẾT LUẬN: ...”. Sau đó tối đa các khối cần thiết: “MUA MỚI:”, “NẾU ĐANG NẮM GIỮ:”, “VÌ SAO:”, “THAM CHIẾU NGHIÊN CỨU:”, “RỦI RO / ĐIỀU KIỆN ĐỔI:”, “DỮ LIỆU:”.
- Với danh mục: “VIỆC CẦN LÀM TRƯỚC:” rồi mã đang sở hữu, watchlist, rủi ro tập trung, mã thiếu dữ liệu.
- Với RESEARCH_ONLY, ghi cuối: “Góc nhìn nghiên cứu — chưa phải tín hiệu hành động đã được xác nhận.”
- Với REFERENCE_ONLY, ghi cuối: “Dữ liệu tham chiếu — mã chưa đạt research-ready, không dùng như tín hiệu hành động.”
- Nếu câu hỏi cụ thể, trả lời đúng ý đó trước. Không lặp lại cùng một trạng thái bằng nhiều câu.`;

export function stockRadarMode(actionReady, researchReady, referenceReady = false) {
  if (actionReady) return 'ACTION_READY';
  if (researchReady) return 'RESEARCH_ONLY';
  if (referenceReady) return 'REFERENCE_ONLY';
  return 'METHOD_ONLY';
}

function obj(value) { return value && typeof value === 'object' && !Array.isArray(value) ? value : {}; }
function num(value) { const n = Number(value); return Number.isFinite(n) ? n : null; }
function txt(value) { return typeof value === 'string' ? value.trim() : value == null ? '' : String(value).trim(); }
function fmtNumber(value, digits = 2) { const n = num(value); return n == null ? '' : n.toLocaleString('vi-VN', { maximumFractionDigits: digits }); }
function fmtPrice(value) { const n = num(value); return n == null ? '' : `${Math.round(n).toLocaleString('vi-VN')}đ`; }
function fmtPct(value, digits = 1) { const n = num(value); return n == null ? '' : `${n.toLocaleString('vi-VN', { maximumFractionDigits: digits })}%`; }
function pctFrom(price, target) { const p = num(price), t = num(target); return p && t != null ? ((t / p) - 1) * 100 : null; }
function merge(...values) { return Object.assign({}, ...values.map(obj)); }

function state(value) {
  let s = txt(value).replaceAll('_', ' ').replace(/\s+/g, ' ').trim();
  const exact = {
    'WATCH': 'THEO DÕI',
    'THEO DOI': 'THEO DÕI',
    'THEO DOI KHONG HANH DONG': 'THEO DÕI — CHƯA HÀNH ĐỘNG',
    'KHONG HANH DONG': 'CHƯA HÀNH ĐỘNG',
    'HA TY TRONG HOAC BAN': 'HẠ TỶ TRỌNG HOẶC BÁN',
    'GIU': 'GIỮ',
    'GIU QUAN SAT': 'GIỮ VÀ QUAN SÁT',
    'PHAN HOA THAN TRONG': 'PHÂN HÓA, THẬN TRỌNG',
    'LAGGING': 'YẾU HƠN THỊ TRƯỜNG',
    'LEADING': 'DẪN DẮT',
    'WEAK': 'YẾU',
    'NEUTRAL': 'TRUNG TÍNH',
    'STRONG': 'MẠNH',
    'RESEARCH READY WATCH': 'THEO DÕI — DỮ LIỆU NGHIÊN CỨU SẴN SÀNG',
  };
  if (exact[s.toUpperCase()]) return exact[s.toUpperCase()];
  return s.replace(/\bWATCH\b/gi, 'THEO DÕI').replace(/\bTHEO DOI\b/gi, 'THEO DÕI').replace(/\bKHONG HANH DONG\b/gi, 'CHƯA HÀNH ĐỘNG');
}

const REASONS = {
  NO_BUY_SETUP: 'chưa có setup mua đạt chuẩn',
  MISSING_ACTION_MAP: 'chưa có bản đồ hành động đủ điều kiện phát hành',
  UPSIDE_TOO_LOW: 'dư địa tăng tại điểm vào hiện tại chưa đủ hấp dẫn',
  RR_BELOW_2: 'Risk/Reward dưới 2',
  CURRENT_CORPORATE_ACTION_UNVERIFIED: 'cần xác minh thêm sự kiện/quyền doanh nghiệp hiện tại',
  RESEARCH_OR_DATA_GATE_NOT_READY: 'dữ liệu nghiên cứu chưa đạt chuẩn',
  SCAN_SLA_NOT_READY: 'dữ liệu quét trong phiên chưa đạt SLA',
  AUTHORITATIVE_CORPORATE_ACTION_SOURCE_UNAVAILABLE: 'nguồn sự kiện/quyền doanh nghiệp chính thức chưa sẵn sàng',
  DATA_RIGHTS: 'quyền dữ liệu công khai chưa hoàn tất',
  COMPLIANCE: 'kiểm tra tuân thủ công khai chưa hoàn tất',
  ACTIVE_PRODUCTION_MANIFEST: 'chưa có production manifest đang hoạt động',
};
function reasonArray(value, corporateActionClear = false) {
  const raw = Array.isArray(value) ? value : txt(value).split('|');
  return raw.map(v => txt(v)).filter(Boolean)
    .filter(v => !(corporateActionClear && v === 'CURRENT_CORPORATE_ACTION_UNVERIFIED'))
    .map(v => REASONS[v] || state(v));
}
function reasons(value, corporateActionClear = false) { return reasonArray(value, corporateActionClear).join('; '); }
function questionIntent(question) {
  const q = txt(question).toLowerCase();
  if (/(rủi ro|rui ro|risk|downside|nguy cơ|nguy co)/i.test(q)) return 'RISK';
  if (/(3\s*[-–]\s*6|3\s*đến\s*6|3\s*den\s*6|trung hạn|trung han)/i.test(q)) return 'MEDIUM';
  if (/(12\s*tháng|12\s*thang|dài hạn|dai han|tích sản|tich san)/i.test(q)) return 'LONG';
  if (/(đang nắm|dang nam|nắm giữ|nam giu|đang giữ|dang giu|có hàng|co hang|giữ thế nào|giu the nao)/i.test(q)) return 'HOLD';
  if (/(catalyst|tin tức|tin tuc|sự kiện|su kien)/i.test(q)) return 'CATALYST';
  if (/(định giá|dinh gia|fair value|p\/e|p\/b)/i.test(q)) return 'VALUE';
  if (/(mua|điểm mua|diem mua|vào được|vao duoc)/i.test(q)) return 'BUY';
  return 'GENERAL';
}

export function normalizeResearchContext(raw) {
  if (!raw || !['INTERNAL_RESEARCH_READY', 'INTERNAL_REFERENCE_READY'].includes(raw.status)) return null;
  const p = obj(raw.payload);
  const rv7 = obj(p.research_v7), quote = obj(p.quote), setup = obj(p.setup), scores = obj(p.scores), risk = obj(p.risk), market = obj(p.market_context), plan = obj(p.trade_plan), fv = obj(p.fundamental_valuation);
  const contextGrade = txt(raw.context_grade) || (raw.status === 'INTERNAL_RESEARCH_READY' ? 'RESEARCH_READY' : 'REFERENCE_ONLY');
  return {
    status: 'CONTEXT_READY', context_grade: contextGrade, ticker: raw.ticker, snapshot_id: raw.snapshot_id,
    generated_at: raw.generated_at, as_of_date: raw.as_of_date,
    price_snapshot_status: raw.price_snapshot_status, public_action_allowed: false,
    company_type: p.company_type, sector: p.sector, business_bucket: p.business_bucket, profile: p.profile,
    quote, setup, scores, risk, market_context: market, trade_plan: plan,
    analysis: merge(rv7, quote, setup, scores, risk, market, p.analysis),
    technical_detail: merge(rv7, setup, scores, risk, p.technical_detail),
    valuation_detail: merge(rv7, plan, fv, p.valuation_detail),
    fundamental_detail: merge(rv7, fv, scores, p.fundamental_detail),
    scanner_postclose: merge(rv7, quote, setup, scores, risk, market, plan, p.scanner_postclose),
    catalyst: obj(p.catalyst), corporate_action: obj(p.corporate_action),
    supply_institutional: obj(p.supply_institutional), fundamental_valuation: fv,
    release: obj(p.release), research_v7: rv7,
  };
}

function singleResearch(context, question = '', reference = false) {
  const ticker = txt(context.ticker) || 'Mã đang hỏi';
  const a = obj(context.analysis), tech = obj(context.technical_detail), post = obj(context.scanner_postclose), plan = obj(context.trade_plan), catalyst = obj(context.catalyst), score = obj(context.scores), corp = obj(context.corporate_action), quote = obj(context.quote), supply = obj(context.supply_institutional);
  const price = num(quote.price) ?? num(a.price) ?? num(post.price);
  const setup = state(obj(context.setup).candidate_setup || a.candidate_setup || post.candidate_setup || post.setup_internal || a.radar_status_v7 || a.radar_status_v6);
  const newState = state(obj(context.setup).new_position_state_v5 || a.new_position_state_v5);
  const holdState = state(obj(context.setup).holding_state_v5 || a.holding_state_v5);
  const waiting = setup.includes('THEO DÕI') || newState.includes('THEO DÕI') || newState.includes('CHƯA HÀNH ĐỘNG') || !setup;
  const t36 = num(plan.target_3_6m ?? a.target_3_6m_v5), t12 = num(plan.target_12m ?? a.target_12m_v5);
  const up36 = pctFrom(price, t36), up12 = pctFrom(price, t12);
  const corporateActionClear = corp.execution_clear_v7 === true || corp.gate_v2 === 'PASS_NO_NEAR_SENSITIVE_EVENT';
  const riskReasons = reasonArray(a.decision_block_reasons_v5 || obj(context.risk).decision_block_reasons_v5, corporateActionClear);
  const intent = questionIntent(question);

  let conclusion;
  if (reference) {
    conclusion = `KẾT LUẬN: ${ticker} có dữ liệu tham chiếu nhưng CHƯA ĐẠT research-ready; chưa dùng để quyết định mua/bán.`;
  } else if (intent === 'RISK' && riskReasons.length) {
    conclusion = `KẾT LUẬN: Rủi ro chính của ${ticker}: ${riskReasons.slice(0, 3).join('; ')}.${waiting ? ' Chưa phù hợp mua mới.' : ''}`;
  } else if (intent === 'MEDIUM' && up36 != null) {
    const view = up36 < 0 ? 'mức tham chiếu nghiên cứu đang thấp hơn giá hiện tại' : up36 < 10 ? 'dư địa nghiên cứu còn mỏng' : 'vẫn còn dư địa nghiên cứu';
    conclusion = `KẾT LUẬN: ${ticker} trong 3–6 tháng ${view} (${up36 >= 0 ? '+' : ''}${fmtPct(up36)}). ${waiting ? 'Chưa mua mới ở thời điểm hiện tại.' : 'Chưa có tín hiệu hành động được xác nhận.'}`;
  } else if (intent === 'LONG' && up12 != null) {
    conclusion = `KẾT LUẬN: ${ticker} tham chiếu nghiên cứu 12 tháng còn ${up12 >= 0 ? '+' : ''}${fmtPct(up12)} so với giá hiện tại; ${waiting ? 'chưa mua mới vì setup hiện tại chưa đạt.' : 'vẫn cần tín hiệu hành động được xác nhận.'}`;
  } else if (intent === 'HOLD' && holdState) {
    conclusion = `KẾT LUẬN: Nếu đang nắm giữ ${ticker}: ${holdState}.${waiting ? ' Không mua thêm ở thời điểm hiện tại.' : ''}`;
  } else {
    conclusion = waiting
      ? `KẾT LUẬN: ${ticker} CHƯA MUA MỚI. Tiếp tục theo dõi và chờ setup/dòng tiền xác nhận.`
      : `KẾT LUẬN: ${ticker} chưa có tín hiệu hành động được xác nhận; tiếp tục theo dõi setup hiện tại.`;
  }
  const lines = [conclusion];

  if (!reference) {
    const buy = [];
    if (newState) buy.push(`trạng thái ${newState}`);
    const pivot = num(tech.pivot20 ?? tech.pivot), distance = num(tech.distance_to_pivot_pct), rvol = num(tech.rvol_progress_adjusted ?? tech.rvol);
    if (pivot != null && distance != null) buy.push(`pivot ${fmtPrice(pivot)}, hiện ${distance < 0 ? 'dưới' : 'trên'} khoảng ${fmtPct(Math.abs(distance))}`);
    if (rvol != null) buy.push(`RVOL ${fmtNumber(rvol)}x`);
    if (tech.pocket_pivot_volume_pass !== undefined) buy.push(`Pocket Pivot volume ${tech.pocket_pivot_volume_pass === true ? 'đạt' : 'chưa đạt'}`);
    if (buy.length) lines.push(`MUA MỚI: ${buy.join('; ')}.`);
  }

  if (holdState) lines.push(`NẾU ĐANG NẮM GIỮ: trạng thái nghiên cứu ${holdState}. Chỉ coi là tín hiệu hành động chính thức khi được xác nhận.`);

  const why = [];
  if (price != null) why.push(`giá ${fmtPrice(price)}`);
  if (setup) why.push(`setup ${setup}`);
  const radarScore = num(score.radar_score_v7 ?? a.radar_score_v7 ?? a.radar_score_v6), fundamentalScore = num(score.fundamental_domain_score_v4 ?? a.fundamental_domain_score_v4), technicalScore = num(score.technical_score ?? a.technical_score), flowScore = num(score.flow_score_v4 ?? a.flow_score_v4), valuationScore = num(score.valuation_domain_score_v4 ?? a.valuation_domain_score_v4), sectorScore = num(score.sector_strength_score ?? a.sector_strength_score), marketScore = num(score.market_score ?? a.market_score), supplyScore = num(score.supply_demand_score_v1 ?? a.supply_demand_score_v1), liquidityScore = num(score.liquidity_score_v4 ?? a.liquidity_score_v4);
  if (radarScore != null) why.push(`Radar Score ${fmtNumber(radarScore,1)}/100`);
  if (fundamentalScore != null) why.push(`cơ bản ${fmtNumber(fundamentalScore,1)}/100`);
  if (technicalScore != null) why.push(`kỹ thuật ${fmtNumber(technicalScore,1)}/100`);
  if (flowScore != null) why.push(`dòng tiền ${fmtNumber(flowScore,1)}/100`);
  if (valuationScore != null) why.push(`định giá ${fmtNumber(valuationScore,1)}/100`);
  if (sectorScore != null) why.push(`sức mạnh ngành ${fmtNumber(sectorScore,1)}/100`);
  if (marketScore != null) why.push(`thị trường ${fmtNumber(marketScore,1)}/100`);
  if (supplyScore != null) why.push(`cung/cầu ${fmtNumber(supplyScore,1)}/100`);
  if (liquidityScore != null) why.push(`thanh khoản ${fmtNumber(liquidityScore,1)}/100`);
  const marketRegime = state(obj(context.market_context).market_regime || a.market_regime), sectorRegime = state(obj(context.market_context).sector_regime || a.sector_regime);
  if (marketRegime) why.push(`bối cảnh ${marketRegime}`);
  if (sectorRegime) why.push(`ngành ${sectorRegime}`);
  if (why.length) lines.push(`VÌ SAO: ${why.join(' · ')}.`);

  const refs = [];
  if (t36 != null) refs.push(`3–6 tháng ${fmtPrice(t36)}${up36 != null ? ` (${up36 >= 0 ? '+' : ''}${fmtPct(up36)})` : ''}`);
  if (t12 != null) refs.push(`12 tháng ${fmtPrice(t12)}${up12 != null ? ` (${up12 >= 0 ? '+' : ''}${fmtPct(up12)})` : ''}`);
  if (refs.length) lines.push(`${reference ? 'THAM CHIẾU SƠ BỘ' : 'THAM CHIẾU NGHIÊN CỨU'}: ${refs.join(' · ')}.${reference ? '' : ' Đây không phải Target hành động đã phát hành.'}`);

  const catTitle = txt(catalyst.latest_official_title_v3 || catalyst.latest_official_title || a.latest_official_catalyst_title_v3 || a.latest_catalyst_title_v2);
  const catTime = txt(catalyst.latest_official_time_v3 || catalyst.latest_official_time || a.latest_official_catalyst_time_v3 || a.latest_catalyst_time_v2);
  if (intent === 'CATALYST' && !catTitle) lines.push('CATALYST: snapshot hiện chưa có sự kiện chính thức đủ rõ để nêu.');
  else if (catTitle) lines.push(`CATALYST: ${catTitle}${catTime ? ` (${catTime})` : ''}.`);

  const riskBits = [...riskReasons];
  const dd = num(obj(context.risk).max_drawdown60_pct ?? a.max_drawdown60_pct), vol = num(obj(context.risk).realized_vol20_pct ?? a.realized_vol20_pct), atr = num(obj(context.risk).atr20_pct ?? a.atr20_pct);
  if (atr != null) riskBits.push(`ATR20 ${fmtPct(atr)}`);
  if (dd != null) riskBits.push(`drawdown 60 phiên ${fmtPct(dd)}`);
  if (vol != null) riskBits.push(`biến động thực hiện 20 phiên ${fmtPct(vol)}`);
  if (corp.review_required_v2 === true) riskBits.push('corporate action cần rà soát');
  if (riskBits.length) lines.push(`RỦI RO / ĐIỀU KIỆN ĐỔI: ${riskBits.join('; ')}.`);

  const supplyBits = [];
  if (num(supply.free_float_proxy_pct) != null) supplyBits.push(`free-float proxy ${fmtPct(supply.free_float_proxy_pct)}`);
  if (num(supply.float_turnover20_pct) != null) supplyBits.push(`turnover20 ${fmtPct(supply.float_turnover20_pct, 2)}`);
  if (supplyBits.length && ['BUY','RISK','GENERAL'].includes(intent)) lines.push(`CUNG / TỔ CHỨC: ${supplyBits.join(' · ')}.`);

  const asOf = txt(context.as_of_date) || txt(context.generated_at);
  if (asOf) lines.push(`DỮ LIỆU: ${asOf}.`);
  lines.push(reference ? 'Dữ liệu tham chiếu — mã chưa đạt research-ready, không dùng như tín hiệu hành động.' : 'Góc nhìn nghiên cứu — chưa phải tín hiệu hành động đã được xác nhận.');
  return lines.join('\n\n');
}

function actionAnswer(list) {
  const rows = [];
  for (const report of list.slice(0, 6)) {
    const p = obj(report.payload), plan = merge(p.trade_plan, p.action, p.recommendation), ticker = txt(report.ticker), horizon = txt(report.horizon);
    const bits = [];
    const action = state(plan.action || plan.signal || plan.state || p.action_state || p.recommendation_state);
    if (action) bits.push(action);
    const low = num(plan.buy_zone_low), high = num(plan.buy_zone_high), stop = num(plan.stop_loss), near = num(plan.target_near), t36 = num(plan.target_3_6m), t12 = num(plan.target_12m), rr = num(plan.risk_reward_to_base);
    if (low != null || high != null) bits.push(`Buy Zone ${low != null ? fmtPrice(low) : '?'}–${high != null ? fmtPrice(high) : '?'}`);
    if (stop != null) bits.push(`Stop ${fmtPrice(stop)}`);
    if (near != null) bits.push(`Target gần ${fmtPrice(near)}`);
    if (t36 != null) bits.push(`Target 3–6T ${fmtPrice(t36)}`);
    if (t12 != null) bits.push(`Target 12T ${fmtPrice(t12)}`);
    if (rr != null) bits.push(`R/R ${fmtNumber(rr,2)}`);
    rows.push(`${ticker}${horizon ? ` ${horizon}` : ''}: ${bits.length ? bits.join(' · ') : 'Action Report READY; dùng các trường đã phát hành trong báo cáo.'}`);
  }
  return `KẾT LUẬN: StockRadar đã có ${list.length} Action Report đủ điều kiện phát hành.\n\n${rows.join('\n')}\n\nChỉ sử dụng các mức đã có trong Action Report; không tự suy diễn thêm.`;
}

export function deterministicStockRadarAnswer({ mode, researchContext, actionContext, question = '' }) {
  const list = Array.isArray(researchContext) ? researchContext.filter(Boolean) : researchContext ? [researchContext] : [];
  if (mode === 'RESEARCH_ONLY' && list.length === 1) return singleResearch(list[0], question);
  if (mode === 'REFERENCE_ONLY' && list.length === 1) return singleResearch(list[0], question, true);
  if ((mode === 'RESEARCH_ONLY' || mode === 'REFERENCE_ONLY') && list.length > 1) {
    const rows = list.slice(0, 20).map(c => {
      const a = obj(c.analysis), score = obj(c.scores), price = num(obj(c.quote).price) ?? num(a.price), setup = state(obj(c.setup).candidate_setup || a.candidate_setup || a.radar_status_v7 || a.radar_status_v6), radar = num(score.radar_score_v7 ?? a.radar_score_v7 ?? a.radar_score_v6), grade = txt(c.context_grade) === 'RESEARCH_READY' ? 'READY' : 'REF';
      return `- ${txt(c.ticker)}: ${price != null ? fmtPrice(price) : 'chưa có giá'}${setup ? ` · ${setup}` : ''}${radar != null ? ` · Radar ${fmtNumber(radar,1)}` : ''} · ${grade}`;
    });
    return `VIỆC CẦN LÀM TRƯỚC: ưu tiên mã READY có setup rõ, điểm kỹ thuật/dòng tiền tốt và ít điểm chặn hơn.\n\n${rows.join('\n')}\n\nMã REF chỉ là dữ liệu tham chiếu, không dùng như tín hiệu hành động.`;
  }
  if (mode === 'ACTION_READY' && Array.isArray(actionContext) && actionContext.length) return actionAnswer(actionContext);
  return 'KẾT LUẬN: chưa có snapshot đủ mới cho mã này. StockRadar AI không dùng giá hoặc tín hiệu cũ để suy đoán.';
}
