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
- METHOD_ONLY: chưa đủ dữ liệu hiện tại; nói rõ dữ liệu nào còn thiếu, không tự suy đoán.

CÁCH TRẢ LỜI — BẮT BUỘC
- Tiếng Việt, ngắn, rõ, quyết định trước. Không viết kiểu báo cáo kỹ thuật dài dòng.
- Không dùng ký hiệu Markdown như ** vì giao diện hiển thị văn bản thuần.
- Không dùng thuật ngữ nội bộ “Action Gate”, “Data Gate”; nói “tín hiệu hành động được xác nhận” hoặc “dữ liệu đủ điều kiện phát hành”.
- Với một mã, dòng đầu tiên phải là “KẾT LUẬN: ...”. Sau đó tối đa các khối cần thiết: “MUA MỚI:”, “NẾU ĐANG NẮM GIỮ:”, “VÌ SAO:”, “THAM CHIẾU NGHIÊN CỨU:”, “RỦI RO / ĐIỀU KIỆN ĐỔI:”, “DỮ LIỆU:”.
- Với danh mục: “VIỆC CẦN LÀM TRƯỚC:” rồi mã đang sở hữu, watchlist, rủi ro tập trung, mã thiếu dữ liệu.
- Với RESEARCH_ONLY, ghi cuối: “Góc nhìn nghiên cứu — chưa phải tín hiệu hành động đã được xác nhận.”
- Nếu câu hỏi cụ thể, trả lời đúng ý đó trước. Không lặp lại cùng một trạng thái bằng nhiều câu.`;

export function stockRadarMode(actionReady, researchReady) {
  if (actionReady) return 'ACTION_READY';
  if (researchReady) return 'RESEARCH_ONLY';
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
    'PHAN HOA THAN TRONG': 'PHÂN HÓA, THẬN TRỌNG',
    'LAGGING': 'YẾU HƠN THỊ TRƯỜNG',
    'LEADING': 'DẪN DẮT',
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
  DATA_RIGHTS: 'quyền dữ liệu công khai chưa hoàn tất',
  COMPLIANCE: 'kiểm tra tuân thủ công khai chưa hoàn tất',
  ACTIVE_PRODUCTION_MANIFEST: 'chưa có production manifest đang hoạt động',
};
function reasons(value) {
  const raw = Array.isArray(value) ? value : txt(value).split('|');
  return raw.map(v => txt(v)).filter(Boolean).map(v => REASONS[v] || state(v)).join('; ');
}

export function normalizeResearchContext(raw) {
  if (!raw || raw.status !== 'INTERNAL_RESEARCH_READY') return null;
  const p = obj(raw.payload);
  const rv7 = obj(p.research_v7), quote = obj(p.quote), setup = obj(p.setup), scores = obj(p.scores), risk = obj(p.risk), market = obj(p.market_context), plan = obj(p.trade_plan), fv = obj(p.fundamental_valuation);
  return {
    status: 'RESEARCH_READY', ticker: raw.ticker, snapshot_id: raw.snapshot_id,
    generated_at: raw.generated_at, as_of_date: raw.as_of_date,
    price_snapshot_status: raw.price_snapshot_status, public_action_allowed: false,
    profile: p.profile,
    analysis: merge(rv7, quote, setup, scores, risk, market, p.analysis),
    technical_detail: merge(rv7, setup, scores, risk, p.technical_detail),
    valuation_detail: merge(rv7, plan, fv, p.valuation_detail),
    fundamental_detail: merge(rv7, fv, scores, p.fundamental_detail),
    scanner_postclose: merge(rv7, quote, setup, scores, risk, market, plan, p.scanner_postclose),
    risk, scores, trade_plan: plan, catalyst: obj(p.catalyst), market_context: market,
    corporate_action: obj(p.corporate_action), supply_institutional: obj(p.supply_institutional),
    fundamental_valuation: fv, release: p.release,
  };
}

function singleResearch(context) {
  const ticker = txt(context.ticker) || 'Mã đang hỏi';
  const a = obj(context.analysis), tech = obj(context.technical_detail), post = obj(context.scanner_postclose), plan = obj(context.trade_plan), catalyst = obj(context.catalyst), score = obj(context.scores);
  const price = num(a.price) ?? num(post.price);
  const setup = state(a.candidate_setup || post.candidate_setup || post.setup_internal || a.radar_status_v7 || a.radar_status_v6);
  const newState = state(a.new_position_state_v5);
  const holdState = state(a.holding_state_v5);
  const waiting = setup.includes('THEO DÕI') || newState.includes('THEO DÕI') || newState.includes('CHƯA HÀNH ĐỘNG') || !setup;
  const lines = [waiting
    ? `KẾT LUẬN: ${ticker} CHƯA MUA MỚI. Tiếp tục theo dõi và chờ setup/dòng tiền xác nhận.`
    : `KẾT LUẬN: ${ticker} chưa có tín hiệu hành động được xác nhận; tiếp tục theo dõi setup hiện tại.`];

  const buy = [];
  if (newState) buy.push(`trạng thái ${newState}`);
  const pivot = num(tech.pivot20 ?? tech.pivot), distance = num(tech.distance_to_pivot_pct), rvol = num(tech.rvol_progress_adjusted ?? tech.rvol);
  if (pivot != null && distance != null) buy.push(`pivot ${fmtPrice(pivot)}, hiện ${distance < 0 ? 'dưới' : 'trên'} khoảng ${fmtPct(Math.abs(distance))}`);
  if (rvol != null) buy.push(`RVOL ${fmtNumber(rvol)}x`);
  if (tech.pocket_pivot_volume_pass !== undefined) buy.push(`Pocket Pivot volume ${tech.pocket_pivot_volume_pass === true ? 'đạt' : 'chưa đạt'}`);
  if (buy.length) lines.push(`MUA MỚI: ${buy.join('; ')}.`);

  if (holdState) lines.push(`NẾU ĐANG NẮM GIỮ: trạng thái nghiên cứu ${holdState}. Chỉ coi là tín hiệu hành động chính thức khi được xác nhận.`);

  const why = [];
  if (price != null) why.push(`giá ${fmtPrice(price)}`);
  if (setup) why.push(`setup ${setup}`);
  const radarScore = num(score.radar_score_v7 ?? a.radar_score_v7 ?? a.radar_score_v6), fundamentalScore = num(score.fundamental_domain_score_v4 ?? a.fundamental_domain_score_v4), technicalScore = num(score.technical_score ?? a.technical_score), flowScore = num(score.flow_score_v4 ?? a.flow_score_v4), sectorScore = num(score.sector_strength_score ?? a.sector_strength_score);
  if (radarScore != null) why.push(`Radar Score ${fmtNumber(radarScore,1)}/100`);
  if (fundamentalScore != null) why.push(`cơ bản ${fmtNumber(fundamentalScore,1)}/100`);
  if (technicalScore != null) why.push(`kỹ thuật ${fmtNumber(technicalScore,1)}/100`);
  if (flowScore != null) why.push(`dòng tiền ${fmtNumber(flowScore,1)}/100`);
  if (sectorScore != null) why.push(`sức mạnh ngành ${fmtNumber(sectorScore,1)}/100`);
  const marketRegime = state(a.market_regime), sectorRegime = state(a.sector_regime);
  if (marketRegime) why.push(`thị trường ${marketRegime}`);
  if (sectorRegime) why.push(`ngành ${sectorRegime}`);
  if (why.length) lines.push(`VÌ SAO: ${why.join(' · ')}.`);

  const refs = [];
  const t36 = num(plan.target_3_6m ?? a.target_3_6m_v5), t12 = num(plan.target_12m ?? a.target_12m_v5);
  if (t36 != null) { const up = pctFrom(price,t36); refs.push(`3–6 tháng ${fmtPrice(t36)}${up != null ? ` (${up >= 0 ? '+' : ''}${fmtPct(up)})` : ''}`); }
  if (t12 != null) { const up = pctFrom(price,t12); refs.push(`12 tháng ${fmtPrice(t12)}${up != null ? ` (${up >= 0 ? '+' : ''}${fmtPct(up)})` : ''}`); }
  if (refs.length) lines.push(`THAM CHIẾU NGHIÊN CỨU: ${refs.join(' · ')}. Đây không phải Target hành động đã phát hành.`);

  const catTitle = txt(catalyst.latest_official_title_v3 || catalyst.latest_official_title || a.latest_official_catalyst_title_v3 || a.latest_catalyst_title_v2);
  const catTime = txt(catalyst.latest_official_time_v3 || catalyst.latest_official_time || a.latest_official_catalyst_time_v3 || a.latest_catalyst_time_v2);
  if (catTitle) lines.push(`CATALYST: ${catTitle}${catTime ? ` (${catTime})` : ''}.`);

  const riskBits = [];
  const block = reasons(a.decision_block_reasons_v5 || obj(context.risk).decision_block_reasons_v5);
  if (block) riskBits.push(block);
  const dd = num(obj(context.risk).max_drawdown60_pct ?? a.max_drawdown60_pct), vol = num(obj(context.risk).realized_vol20_pct ?? a.realized_vol20_pct);
  if (dd != null) riskBits.push(`drawdown 60 phiên ${fmtPct(dd)}`);
  if (vol != null) riskBits.push(`biến động thực hiện 20 phiên ${fmtPct(vol)}`);
  if (riskBits.length) lines.push(`RỦI RO / ĐIỀU KIỆN ĐỔI: ${riskBits.join('; ')}.`);

  const asOf = txt(context.as_of_date) || txt(context.generated_at);
  if (asOf) lines.push(`DỮ LIỆU: ${asOf}.`);
  lines.push('Góc nhìn nghiên cứu — chưa phải tín hiệu hành động đã được xác nhận.');
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
    if (stop != null) bits.push(`Stop ${fmtPrice(stop)}`); if (near != null) bits.push(`Target gần ${fmtPrice(near)}`); if (t36 != null) bits.push(`Target 3–6T ${fmtPrice(t36)}`); if (t12 != null) bits.push(`Target 12T ${fmtPrice(t12)}`); if (rr != null) bits.push(`R/R ${fmtNumber(rr,2)}`);
    rows.push(`${ticker}${horizon ? ` ${horizon}` : ''}: ${bits.length ? bits.join(' · ') : 'Action Report READY; dùng các trường đã phát hành trong báo cáo.'}`);
  }
  return `KẾT LUẬN: StockRadar đã có ${list.length} Action Report đủ điều kiện phát hành.\n\n${rows.join('\n')}\n\nChỉ sử dụng các mức đã có trong Action Report; không tự suy diễn thêm.`;
}

export function deterministicStockRadarAnswer({ mode, researchContext, actionContext }) {
  const list = Array.isArray(researchContext) ? researchContext.filter(Boolean) : researchContext ? [researchContext] : [];
  if (mode === 'RESEARCH_ONLY' && list.length === 1) return singleResearch(list[0]);
  if (mode === 'RESEARCH_ONLY' && list.length > 1) {
    const rows = list.slice(0, 12).map(c => {
      const a = obj(c.analysis), score = obj(c.scores), price = num(a.price), setup = state(a.candidate_setup || a.radar_status_v7 || a.radar_status_v6), radar = num(score.radar_score_v7 ?? a.radar_score_v7 ?? a.radar_score_v6);
      return `- ${txt(c.ticker)}: ${price != null ? fmtPrice(price) : 'chưa có giá'}${setup ? ` · ${setup}` : ''}${radar != null ? ` · Radar ${fmtNumber(radar,1)}` : ''}`;
    });
    return `VIỆC CẦN LÀM TRƯỚC: ưu tiên mã có setup rõ, điểm kỹ thuật/dòng tiền tốt và ít điểm chặn hơn.\n\n${rows.join('\n')}\n\nGóc nhìn nghiên cứu — chưa phải tín hiệu hành động đã được xác nhận.`;
  }
  if (mode === 'ACTION_READY' && Array.isArray(actionContext) && actionContext.length) return actionAnswer(actionContext);
  return 'KẾT LUẬN: chưa đủ dữ liệu nghiên cứu để kết luận hiện tại. Cần dữ liệu giá, khối lượng, setup/pivot và cơ bản đủ mới để xác nhận.';
}
