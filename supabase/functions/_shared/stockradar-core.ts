import { readableResearchFacts, observationDate, wantsResearchDetail } from "./stockradar-readable.ts";

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
- Tiếng Việt thông dụng, câu ngắn. Với một mã, dòng đầu tiên phải là “KẾT LUẬN: ...”. Mặc định khoảng 150–250 từ, tối đa 3 lý do chính, không liệt kê hàng loạt điểm số.
- Không dùng ký hiệu Markdown như ** vì giao diện hiển thị văn bản thuần.
- Không dùng thuật ngữ nội bộ “Action Gate”, “Data Gate”, research-ready, snapshot, setup. Dùng “điều kiện mua”, “dữ liệu ngày…”.
- Dùng “khối lượng giao dịch”, “mốc giá theo dõi”, “mức giá tham khảo”, “mức cắt lỗ”, “lợi nhuận kỳ vọng so với rủi ro”. Tránh RVOL, Pivot, Target, Stop, Risk/Reward, catalyst, drawdown, free-float, turnover. Nếu người dùng hỏi một thuật ngữ, giải thích bằng tiếng Việt trước.
- Trả lời đúng câu hỏi trước. Với câu hỏi mua hoặc nhận định chung: kết luận, “VÌ SAO:”, “NẾU ĐANG NẮM GIỮ:”, “CẦN CHỜ:”. Chỉ thêm mức giá tham khảo khi hữu ích; ghi rõ đó là ước tính, không phải giá chắc chắn đạt được. Chỉ đưa bảng điểm và chỉ số chuyên sâu khi được hỏi.
- Mọi so sánh giá phải ghi giá quan sát, ngày, mốc so sánh, chênh lệch bằng đồng và phần trăm tính theo mốc. Không viết “hiện dưới khoảng…”. Ưu tiên readable_facts đã tính từ cùng dữ liệu; không suy ngược giá từ phần trăm làm tròn.
- Khối lượng phải ghi so với mức nào, trong phiên hay cuối phiên. 0,73 lần trung bình 20 phiên nghĩa là khoảng 73% trung bình, thấp hơn khoảng 27%. Chỉ điều kiện khối lượng đạt chưa có nghĩa là điểm mua đã được xác nhận. Không dùng cờ ước tính trong phiên để kết luận về cuối phiên; ưu tiên readable_facts.earlyVolumePass.
- Mốc theo dõi không tự động là giá mua. Không tự đặt thêm ngưỡng giá, khối lượng hay điều kiện mua/bán. Nêu rõ điều đang thiếu từ dữ liệu; không khẳng định lợi nhuận/rủi ro dưới 2 nếu thiếu mức cắt lỗ hoặc tỷ lệ cụ thể.
- Không suy luận doanh nghiệp tốt/xấu chỉ từ điểm tổng hợp. Không gán tác động tăng giá cho tin doanh nghiệp chỉ dựa vào tiêu đề.
- Với danh mục: việc cần xem trước, mã đang giữ, mã đang theo dõi và rủi ro chính. Không phơi bày danh mục người khác.
- Với RESEARCH_ONLY, kết thúc bằng “Thông tin tham khảo từ dữ liệu ngày …; chưa có tín hiệu mua/bán được xác nhận.” Với REFERENCE_ONLY, nói rõ dữ liệu còn thiếu để đánh giá mua/bán.
- Nếu data_quality là stale/error, mở đầu cảnh báo dữ liệu cũ hoặc có lỗi; không xác nhận mua/bán từ dữ liệu đó.
- Giá, mức cắt lỗ, mục tiêu hay xác suất không có dữ liệu phải ghi chưa đủ dữ liệu khi người dùng hỏi; không bịa số. Điểm tin cậy không phải xác suất thành công.
- Không lặp lại cùng một trạng thái bằng nhiều câu.`;

export function stockRadarMode(actionReady, researchReady, referenceReady = false) {
  if (actionReady) return 'ACTION_READY';
  if (researchReady) return 'RESEARCH_ONLY';
  if (referenceReady) return 'REFERENCE_ONLY';
  return 'METHOD_ONLY';
}

function obj(value) { return value && typeof value === 'object' && !Array.isArray(value) ? value : {}; }
function num(value) { if (value == null || typeof value === 'boolean' || typeof value === 'object' || String(value).trim() === '') return null; const n = Number(value); return Number.isFinite(n) ? n : null; }
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
  NO_BUY_SETUP: 'giá và khối lượng chưa đáp ứng đủ điều kiện mua',
  MISSING_ACTION_MAP: 'chưa xác định được đầy đủ mức mua, cắt lỗ và chốt lời',
  UPSIDE_TOO_LOW: 'dư địa tăng tại điểm vào hiện tại chưa đủ hấp dẫn',
  RR_BELOW_2: 'lợi nhuận kỳ vọng chưa đạt gấp đôi khoản lỗ dự kiến',
  CURRENT_CORPORATE_ACTION_UNVERIFIED: 'cần xác minh thêm sự kiện/quyền doanh nghiệp hiện tại',
  RESEARCH_OR_DATA_GATE_NOT_READY: 'dữ liệu chưa đủ để đánh giá',
  SCAN_SLA_NOT_READY: 'dữ liệu giao dịch trong phiên chưa được cập nhật đủ',
  AUTHORITATIVE_CORPORATE_ACTION_SOURCE_UNAVAILABLE: 'nguồn sự kiện/quyền doanh nghiệp chính thức chưa sẵn sàng',
  DATA_RIGHTS: 'quyền dữ liệu công khai chưa hoàn tất',
  COMPLIANCE: 'kiểm tra tuân thủ công khai chưa hoàn tất',
  ACTIVE_PRODUCTION_MANIFEST: 'chưa có tín hiệu chính thức được phát hành',
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
  const context = {
    status: 'CONTEXT_READY', context_grade: contextGrade, ticker: raw.ticker, snapshot_id: raw.snapshot_id,
    generated_at: raw.generated_at, as_of_date: raw.as_of_date,
    data_quality: raw.data_quality || 'updated', volume_mode: p.volume_mode || 'UNKNOWN', history: obj(p.history),
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
  const facts = readableResearchFacts(context);
  if (context.volume_mode === 'EOD') {
    context.technical_detail.pocket_pivot_volume_pass = facts.earlyVolumePass;
    context.technical_detail.max_down_volume10 = facts.downMax;
    context.technical_detail.rvol = facts.rvol;
  }
  return { ...context, readable_facts: facts };
}

function singleResearch(context, question = '', reference = false) {
  const ticker = txt(context.ticker) || 'Mã đang hỏi';
  const a = obj(context.analysis), plan = obj(context.trade_plan), setup = obj(context.setup), market = obj(context.market_context), corp = obj(context.corporate_action), catalyst = obj(context.catalyst);
  const facts = readableResearchFacts(context), intent = questionIntent(question), detail = wantsResearchDetail(question);
  const holdState = state(setup.holding_state_v5 || a.holding_state_v5);
  const corporateActionClear = corp.execution_clear_v7 === true || corp.gate_v2 === 'PASS_NO_NEAR_SENSITIVE_EVENT';
  const rawReasons = setup.decision_block_reasons_v5 || a.decision_block_reasons_v5 || obj(context.risk).decision_block_reasons_v5;
  const rr = num(plan.risk_reward_to_base ?? a.rr_to_base_v5);
  const riskReasons = reasonArray(rawReasons, corporateActionClear)
    .filter(r => r !== REASONS.RR_BELOW_2 || (rr != null && rr < 2))
    .filter(r => Object.values(REASONS).includes(r));
  const t36 = num(plan.target_3_6m ?? a.target_3_6m_v5), t12 = num(plan.target_12m ?? a.target_12m_v5);
  const up36 = pctFrom(facts.price, t36), up12 = pctFrom(facts.price, t12);
  let conclusion = `KẾT LUẬN: ${ticker} CHƯA MUA MỚI theo dữ liệu hiện có.`;
  if (reference) conclusion = `KẾT LUẬN: ${ticker} còn thiếu dữ liệu để đánh giá mua/bán.`;
  else if (intent === 'HOLD') conclusion = `KẾT LUẬN: Nếu đang nắm giữ ${ticker}, ${holdState === 'GIỮ VÀ QUAN SÁT' || holdState === 'GIỮ' ? 'tiếp tục giữ và theo dõi; chưa mua thêm theo dữ liệu hiện có.' : 'cần xem lại rủi ro và kế hoạch nắm giữ; chưa có tín hiệu mua/bán được xác nhận.'}`;
  else if (intent === 'RISK') conclusion = `KẾT LUẬN: Rủi ro chính của ${ticker}: ${riskReasons[0] || 'chưa đủ dữ liệu để xác nhận mức rủi ro'}.`;
  else if (intent === 'MEDIUM' && up36 != null) conclusion = `KẾT LUẬN: ${ticker} trong 3–6 tháng có mức giá tham khảo ${fmtPrice(t36)}, ${up36 >= 0 ? 'cao hơn' : 'thấp hơn'} giá đang ghi nhận khoảng ${fmtPct(Math.abs(up36))}. Đây là ước tính, chưa phải lý do đủ để mua.`;
  else if (intent === 'LONG' && up12 != null) conclusion = `KẾT LUẬN: ${ticker} có mức giá tham khảo 12 tháng là ${fmtPrice(t12)}, ${up12 >= 0 ? 'cao hơn' : 'thấp hơn'} giá đang ghi nhận khoảng ${fmtPct(Math.abs(up12))}. Đây là ước tính, chưa phải lý do đủ để mua.`;
  const quality = txt(context.data_quality);
  const lines = [quality === 'stale' ? `KẾT LUẬN: ${ticker} đang có dữ liệu cũ; chưa dùng để xác nhận mua/bán.` : quality === 'error' ? `KẾT LUẬN: Dữ liệu ${ticker} đang có lỗi; chưa dùng để xác nhận mua/bán.` : conclusion];
  const why = [facts.priceText];
  if (facts.volumeText) why.push(facts.volumeText);
  const sectorState = state(market.sector_regime || a.sector_regime), marketState = state(market.market_regime || a.market_regime);
  const backdrop = [];
  if (sectorState === 'YẾU' || sectorState === 'YẾU HƠN THỊ TRƯỜNG') backdrop.push(`Nhóm ngành ${txt(context.sector).toLowerCase() || 'của cổ phiếu'} đang yếu`);
  if (marketState === 'PHÂN HÓA, THẬN TRỌNG') backdrop.push('thị trường chưa tăng đồng đều giữa các nhóm cổ phiếu');
  if (backdrop.length) why.push(`${backdrop.join('; ')}.`);
  lines.push(`VÌ SAO:\n${why.map(x => `- ${x}`).join('\n')}`);
  if (holdState && !reference && !['stale','error'].includes(quality) && intent !== 'HOLD') {
    const holding = holdState === 'GIỮ VÀ QUAN SÁT' || holdState === 'GIỮ'
      ? 'Theo đánh giá hiện có, tiếp tục giữ và theo dõi; chưa mua thêm.'
      : holdState === 'HẠ TỶ TRỌNG HOẶC BÁN'
        ? 'Đánh giá hiện có nghiêng về giảm số cổ phiếu đang giữ; cần kiểm tra điều kiện bán cụ thể trước khi thực hiện.'
        : 'Cần xem lại rủi ro và kế hoạch nắm giữ; chưa đủ thông tin để đưa ra hướng xử lý cụ thể.';
    lines.push(`NẾU ĐANG NẮM GIỮ: ${holding}`);
  }
  if (!reference && !['stale','error'].includes(quality) && (intent === 'GENERAL' || intent === 'BUY' || intent === 'HOLD')) {
    lines.push(`CẦN CHỜ: ${facts.pivot != null && facts.pivot > 0 ? `Theo dõi phản ứng của giá tại mốc ${fmtPrice(facts.pivot)} và khối lượng giao dịch. Chạm hoặc vượt mốc này chưa tự động đủ điều kiện mua.` : 'Cần có thêm dữ liệu giá và khối lượng để xác nhận điều kiện mua.'}`);
  }
  if (/volume|khối lượng|khoi luong|thanh khoản|thanh khoan|pocket|điểm mua sớm|diem mua som/i.test(question) || detail) lines.push(`KHỐI LƯỢNG VÀ ĐIỂM MUA: ${facts.earlyVolumeText}`);
  if (['VALUE','MEDIUM','LONG','GENERAL'].includes(intent) || detail) {
    const refs = [];
    if (t36 != null && intent !== 'LONG') refs.push(`3–6 tháng: ${fmtPrice(t36)}${up36 != null ? ` (${up36 >= 0 ? '+' : ''}${fmtPct(up36)} so với giá ghi nhận)` : ''}`);
    if (t12 != null && intent !== 'MEDIUM') refs.push(`12 tháng: ${fmtPrice(t12)}${up12 != null ? ` (${up12 >= 0 ? '+' : ''}${fmtPct(up12)} so với giá ghi nhận)` : ''}`);
    if (refs.length) lines.push(`GIÁ THAM KHẢO: ${refs.join('; ')}. Đây là ước tính${obj(context.valuation_detail).assumptions_verified === false ? ' với giả định chưa được xác minh' : ''}, không bảo đảm giá sẽ đạt tới.`);
    else if (intent !== 'GENERAL') lines.push('GIÁ THAM KHẢO: Chưa đủ dữ liệu để xác định.');
  }
  if (intent === 'RISK' || detail) {
    const bits = riskReasons.slice(0, 3);
    if (num(plan.stop_loss) == null) bits.push('chưa có mức cắt lỗ cụ thể để tính khoản lỗ dự kiến');
    if (corp.review_required_v2 === true) bits.push('cần kiểm tra sự kiện doanh nghiệp sắp tới');
    if (bits.length) lines.push(`RỦI RO: ${bits.join('; ')}.`);
  }
  if (intent === 'CATALYST' || detail || corp.review_required_v2 === true) {
    const title = txt(catalyst.latest_official_title_v3 || catalyst.latest_official_title || a.latest_official_catalyst_title_v3 || a.latest_catalyst_title_v2);
    const date = txt(catalyst.latest_official_time_v3 || catalyst.latest_official_time || a.latest_official_catalyst_time_v3 || a.latest_catalyst_time_v2);
    if (title) lines.push(`TIN DOANH NGHIỆP: ${title}${date ? ` (${observationDate(date)})` : ''}. Chưa đủ cơ sở từ tiêu đề để kết luận tin này làm giá tăng hay giảm.`);
    else if (intent === 'CATALYST') lines.push('TIN DOANH NGHIỆP: Chưa có tin chính thức đủ rõ trong dữ liệu hiện có.');
  }
  lines.push(`Thông tin tham khảo từ dữ liệu ngày ${facts.date}; ${reference ? 'còn thiếu dữ liệu để đánh giá mua/bán' : 'chưa có tín hiệu mua/bán được xác nhận'}.`);
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
    if (low != null || high != null) bits.push(`Vùng giá mua ${low != null ? fmtPrice(low) : '?'}–${high != null ? fmtPrice(high) : '?'}`);
    if (stop != null) bits.push(`Mức cắt lỗ ${fmtPrice(stop)}`);
    if (near != null) bits.push(`Giá mục tiêu ngắn hạn ${fmtPrice(near)}`);
    if (t36 != null) bits.push(`Giá mục tiêu 3–6 tháng ${fmtPrice(t36)}`);
    if (t12 != null) bits.push(`Giá mục tiêu 12 tháng ${fmtPrice(t12)}`);
    if (rr != null) bits.push(`Lợi nhuận kỳ vọng / khoản lỗ dự kiến ${fmtNumber(rr,2)}`);
    rows.push(`${ticker}${horizon ? ` (${({SHORT_TERM:'ngắn hạn',MEDIUM_TERM:'3–6 tháng',LONG_TERM:'12 tháng',ACCUMULATION:'tích lũy'})[horizon] || 'kỳ hạn trong báo cáo'})` : ''}: ${bits.length ? bits.join(' · ') : 'Đã có báo cáo hành động; dùng các mức được công bố trong báo cáo.'}`);
  }
  return `KẾT LUẬN: StockRadar đã có ${list.length} báo cáo hành động đủ điều kiện phát hành.\n\n${rows.join('\n')}\n\nChỉ sử dụng các mức đã có trong báo cáo hành động; không tự suy diễn thêm.`;
}

export function deterministicStockRadarAnswer({ mode, researchContext, actionContext, question = '' }) {
  const list = Array.isArray(researchContext) ? researchContext.filter(Boolean) : researchContext ? [researchContext] : [];
  if (mode === 'RESEARCH_ONLY' && list.length === 1) return singleResearch(list[0], question);
  if (mode === 'REFERENCE_ONLY' && list.length === 1) return singleResearch(list[0], question, true);
  if ((mode === 'RESEARCH_ONLY' || mode === 'REFERENCE_ONLY') && list.length > 1) {
    const rows = list.slice(0, 20).map(c => {
      const a = obj(c.analysis), score = obj(c.scores), price = num(obj(c.quote).price) ?? num(a.price), setup = state(obj(c.setup).candidate_setup || a.candidate_setup || a.radar_status_v7 || a.radar_status_v6), radar = num(score.radar_score_v7 ?? a.radar_score_v7 ?? a.radar_score_v6), grade = txt(c.context_grade) === 'RESEARCH_READY' ? 'đủ dữ liệu nghiên cứu' : 'chỉ có dữ liệu tham chiếu';
      return `- ${txt(c.ticker)}: ${price != null ? `${fmtPrice(price)} (ngày ${observationDate(c.as_of_date)})` : 'chưa có giá'}${setup ? ` · ${setup}` : ''}${radar != null ? ` · Điểm tổng hợp ${fmtNumber(radar,1)}/100` : ''} · ${grade}`;
    });
    return `VIỆC CẦN LÀM TRƯỚC: xem các mã có đủ dữ liệu nghiên cứu trước. Danh sách dưới đây dùng để so sánh, chưa phải danh sách nên mua.\n\n${rows.join('\n')}\n\nMã chỉ có dữ liệu tham chiếu cần bổ sung thông tin trước khi đánh giá mua/bán.`;
  }
  if (mode === 'ACTION_READY' && Array.isArray(actionContext) && actionContext.length) return actionAnswer(actionContext);
  return 'KẾT LUẬN: chưa có dữ liệu đủ mới cho mã này. StockRadar AI không dùng giá hoặc tín hiệu cũ để suy đoán.';
}
