export const STOCKRADAR_SYSTEM_CORE = `Bạn là StockRadar AI — trợ lý phân tích cổ phiếu HOSE của StockRadar.

PHẠM VI
- Chỉ phân tích cổ phiếu HOSE; không phân tích Crypto/Coin, HNX hay UPCoM.
- Không tiết lộ mã ưu tiên vận hành nội bộ, danh mục cá nhân ẩn hay logic riêng không có trong dữ liệu người dùng được phép thấy.
- Không yêu cầu mật khẩu, OTP, mã giao dịch hay quyền đặt lệnh.

LÕI PHÂN TÍCH
4M/Payback → CANSLIM → định giá đa phương pháp Bear/Base/Bull → SEPA/VCP/Stage → VPA → Pocket Pivot/Early Momentum → Ichimoku/Bollinger/Trendline → dòng tiền/thị trường → quản trị rủi ro.
Không mua chỉ vì rẻ; không mua doanh nghiệp tốt tại điểm kỹ thuật xấu; không mua đuổi khi quá extended; không bình quân giá xuống khi luận điểm bị phá vỡ.

CHẾ ĐỘ DỮ LIỆU
- ACTION_READY: chỉ dùng ACTION_CONTEXT cho Buy Zone, Stop, Target, Upside/Downside và Risk/Reward; không tự bịa số còn thiếu.
- RESEARCH_ONLY: được phân tích đầy đủ RESEARCH_CONTEXT hiện có. Phải trả lời hữu ích và trực tiếp, nhưng không biến dữ liệu nghiên cứu thành lệnh MUA/BÁN, Buy Zone, Stop hay Target chính thức. Nhãn “Góc nhìn nghiên cứu — chưa phải khuyến nghị hành động đã xác nhận” đặt ở cuối, không dùng làm câu mở đầu.
- METHOD_ONLY: không có đủ dữ liệu hiện tại; không tự tạo dữ kiện.

CÁCH TRẢ LỜI
- Dòng đầu tiên phải là **Kết luận:** và trả lời thẳng câu hỏi bằng 1–2 câu.
- Nếu người dùng hỏi một mã, ưu tiên thứ tự: Kết luận → Mua mới → Nếu đang nắm giữ → 3–5 lý do quan trọng nhất → rủi ro/điều kiện thay đổi → ngày dữ liệu.
- Với RESEARCH_ONLY, nếu trạng thái dữ liệu là WATCH/THEO_DOI_KHONG_HANH_DONG thì nói rõ “chưa mua mới / tiếp tục theo dõi”; nếu holding_state là GIU_QUAN_SAT thì nói rõ “nếu đang giữ: giữ/quan sát”, nhưng ghi đây là trạng thái nghiên cứu, không phải tín hiệu giao dịch chính thức.
- Không mở đầu bằng diễn giải phương pháp, disclaimer hay câu “đã có dữ liệu”. Không dùng câu chung chung kiểu “dùng trạng thái trên và chờ Action Gate” nếu dữ liệu đã có setup, điểm số, giá, trạng thái vị thế hoặc rủi ro cụ thể.
- Chỉ nêu con số có trong ACTION_CONTEXT/RESEARCH_CONTEXT/USER_CONTEXT hoặc phép tính trực tiếp từ chúng. Không gọi score là xác suất nếu chưa có calibration.
- Tiếng Việt, ngắn gọn, dễ hành động.`;

export type StockRadarMode = "ACTION_READY" | "RESEARCH_ONLY" | "METHOD_ONLY";
type JsonObject = Record<string, unknown>;

export function stockRadarMode(actionReady: boolean, researchReady: boolean): StockRadarMode {
  if (actionReady) return "ACTION_READY";
  if (researchReady) return "RESEARCH_ONLY";
  return "METHOD_ONLY";
}

function objectValue(value: unknown): JsonObject {
  return value && typeof value === "object" && !Array.isArray(value) ? value as JsonObject : {};
}

function mergeObjects(...values: unknown[]): JsonObject {
  return Object.assign({}, ...values.map(objectValue));
}

function numberValue(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function textValue(value: unknown): string {
  return typeof value === "string" ? value.trim() : value == null ? "" : String(value).trim();
}

function firstNumber(...values: unknown[]): number | null {
  for (const value of values) {
    const number = numberValue(value);
    if (number !== null) return number;
  }
  return null;
}

function firstText(...values: unknown[]): string {
  for (const value of values) {
    const text = textValue(value);
    if (text) return text;
  }
  return "";
}

function fmtNumber(value: unknown, digits = 2): string {
  const number = numberValue(value);
  if (number === null) return "";
  return number.toLocaleString("vi-VN", { maximumFractionDigits: digits, minimumFractionDigits: 0 });
}

function fmtPrice(value: unknown): string {
  const number = numberValue(value);
  if (number === null) return "";
  return `${Math.round(number).toLocaleString("vi-VN")}đ`;
}

function fmtPct(value: unknown, digits = 1): string {
  const number = numberValue(value);
  return number === null ? "" : `${number.toLocaleString("vi-VN", { maximumFractionDigits: digits, minimumFractionDigits: 0 })}%`;
}

function pctFromTo(from: number | null, to: number | null): number | null {
  if (from === null || to === null || from === 0) return null;
  return ((to / from) - 1) * 100;
}

function humanState(value: unknown): string {
  return textValue(value).replaceAll("_", " ").replace(/\s+/g, " ").trim();
}

function humanBlockers(value: unknown): string[] {
  const raw = textValue(value);
  if (!raw) return [];
  const labels: Record<string, string> = {
    NO_BUY_SETUP: "chưa có setup mua",
    MISSING_ACTION_MAP: "chưa có bản đồ hành động đã phát hành",
    UPSIDE_TOO_LOW: "upside chưa đủ hấp dẫn",
    RR_BELOW_2: "Risk/Reward chưa đạt 2:1",
    CURRENT_CORPORATE_ACTION_UNVERIFIED: "dữ kiện sự kiện doanh nghiệp hiện tại chưa được xác nhận đủ cho hành động",
    DATA_RIGHTS: "quyền dữ liệu chưa hoàn tất",
    COMPLIANCE: "kiểm tra tuân thủ chưa hoàn tất",
    ACTIVE_PRODUCTION_MANIFEST: "bộ dữ liệu production chưa được kích hoạt",
  };
  return raw.split(/[|,]/).map(item => item.trim()).filter(Boolean).map(item => labels[item] || humanState(item).toLowerCase());
}

function scoreLabel(score: number | null): string {
  if (score === null) return "";
  if (score >= 70) return "mạnh";
  if (score >= 55) return "khá";
  if (score >= 45) return "trung tính";
  return "yếu";
}

export function normalizeResearchContext(raw: Record<string, unknown> | null | undefined): Record<string, unknown> | null {
  if (!raw || raw.status !== "INTERNAL_RESEARCH_READY") return null;
  const payload = objectValue(raw.payload);

  // Current validated Drive bundle uses quote/setup/scores/risk/trade_plan/research_v7.
  // Older snapshots used analysis/technical_detail/valuation_detail/fundamental_detail/scanner_postclose.
  // Preserve both schemas and expose compatibility views so the answer engine never discards real data.
  const quote = objectValue(payload.quote);
  const setup = objectValue(payload.setup);
  const scores = objectValue(payload.scores);
  const risk = objectValue(payload.risk);
  const tradePlan = objectValue(payload.trade_plan);
  const researchV7 = objectValue(payload.research_v7);
  const marketContext = objectValue(payload.market_context);
  const fundamentalValuation = objectValue(payload.fundamental_valuation);
  const catalyst = objectValue(payload.catalyst);
  const corporateAction = objectValue(payload.corporate_action);
  const supplyInstitutional = objectValue(payload.supply_institutional);

  const analysis = mergeObjects(
    researchV7,
    payload.analysis,
    quote,
    setup,
    scores,
    marketContext,
    risk,
    tradePlan,
  );
  const technical = mergeObjects(researchV7, payload.technical_detail);
  const valuation = mergeObjects(researchV7, tradePlan, fundamentalValuation, payload.valuation_detail);
  const fundamental = mergeObjects(researchV7, fundamentalValuation, payload.fundamental_detail);
  const postclose = mergeObjects(researchV7, payload.scanner_postclose);

  return {
    status: "RESEARCH_READY",
    ticker: raw.ticker,
    snapshot_id: raw.snapshot_id,
    generated_at: raw.generated_at,
    as_of_date: raw.as_of_date,
    price_snapshot_status: raw.price_snapshot_status,
    public_action_allowed: false,
    data_role: raw.data_role,
    source_ref: raw.source_ref,
    profile: payload.profile,
    company_type: payload.company_type,
    sector: payload.sector,
    business_bucket: payload.business_bucket,
    quote,
    setup,
    scores,
    risk,
    trade_plan: tradePlan,
    research_v7: researchV7,
    market_context: marketContext,
    fundamental_valuation: fundamentalValuation,
    catalyst,
    corporate_action: corporateAction,
    supply_institutional: supplyInstitutional,
    release: payload.release,
    analysis,
    freshness: payload.freshness,
    quick_result: payload.quick_result || setup,
    technical_detail: technical,
    valuation_detail: valuation,
    fundamental_detail: fundamental,
    scanner_postclose: postclose,
  };
}

function singleResearchAnswer(context: JsonObject, question = ""): string {
  const ticker = textValue(context.ticker) || "Mã đang hỏi";
  const quote = objectValue(context.quote);
  const setupObj = objectValue(context.setup);
  const scores = objectValue(context.scores);
  const risk = objectValue(context.risk);
  const trade = objectValue(context.trade_plan);
  const market = objectValue(context.market_context);
  const catalyst = objectValue(context.catalyst);
  const release = objectValue(context.release);
  const analysis = objectValue(context.analysis);
  const technical = objectValue(context.technical_detail);
  const valuation = objectValue(context.valuation_detail);
  const fundamental = objectValue(context.fundamental_detail);
  const postclose = objectValue(context.scanner_postclose);

  const price = firstNumber(quote.price, analysis.price, postclose.price);
  const setup = humanState(firstText(setupObj.candidate_setup, analysis.candidate_setup, postclose.setup_internal, analysis.radar_status_v7, analysis.radar_status_v6));
  const radarStatus = humanState(firstText(setupObj.radar_status_v7, analysis.radar_status_v7, analysis.radar_status_v6));
  const newPositionState = humanState(firstText(setupObj.new_position_state_v5, analysis.new_position_state_v5));
  const holdingState = humanState(firstText(setupObj.holding_state_v5, analysis.holding_state_v5));

  const radarScore = firstNumber(scores.radar_score_v7, scores.radar_score_v6, analysis.radar_score_v7, analysis.radar_score_v6);
  const technicalScore = firstNumber(scores.technical_score, analysis.technical_score);
  const flowScore = firstNumber(scores.flow_score_v4, analysis.flow_score_v4);
  const fundamentalScore = firstNumber(scores.fundamental_domain_score_v4, analysis.fundamental_domain_score_v4);
  const valuationScore = firstNumber(scores.valuation_domain_score_v4, analysis.valuation_domain_score_v4);
  const riskScore = firstNumber(scores.risk_score, analysis.risk_score);
  const marketScore = firstNumber(scores.market_score, analysis.market_score);
  const supplyDemandScore = firstNumber(scores.supply_demand_score_v1, analysis.supply_demand_score_v1);

  const stage = humanState(technical.stage);
  const pivot = firstNumber(technical.pivot20, technical.pivot);
  const pivotDistance = firstNumber(technical.distance_to_pivot_pct);
  const rvol = firstNumber(technical.rvol_progress_adjusted, technical.rvol);
  const ma10 = firstNumber(technical.ma10);
  const ma50 = firstNumber(technical.ma50);
  const ma150 = firstNumber(technical.ma150);
  const ma200 = firstNumber(technical.ma200);

  const pe = firstNumber(postclose.pe_current_calc, fundamental.pe_ttm, fundamental.pe_current_calc);
  const pb = firstNumber(postclose.pb_current_calc, fundamental.pb, fundamental.pb_current_calc);
  const roe = firstNumber(postclose.roe_ttm_pct, fundamental.roe_ttm_pct, fundamental.roe_ttm);
  const revenueGrowth = firstNumber(postclose.revenue_growth_yoy_pct, fundamental.revenue_growth_yoy_pct, fundamental.revenue_growth_yoy);
  const profitGrowth = firstNumber(postclose.pbt_growth_yoy_pct, fundamental.pbt_growth_yoy_pct, fundamental.profit_growth_yoy);

  const fvBear = firstNumber(postclose.fair_value_bootstrap_bear, valuation.fair_value_bear);
  const fvBase = firstNumber(postclose.fair_value_bootstrap_base, valuation.fair_value_base);
  const fvBull = firstNumber(postclose.fair_value_bootstrap_bull, valuation.fair_value_bull);
  const upsideBase = firstNumber(postclose.upside_to_base_pct, valuation.upside_base_pct);
  const research3To6m = firstNumber(trade.target_3_6m, valuation.target_3_6m, valuation.target_3_6m_v5);
  const research12m = firstNumber(trade.target_12m, valuation.target_12m, valuation.target_12m_v5);
  const rr = firstNumber(trade.risk_reward_to_base, valuation.risk_reward_to_base, valuation.rr_to_base_v5);

  const marketRegime = humanState(firstText(market.market_regime, analysis.market_regime));
  const sectorRegime = humanState(firstText(market.sector_regime, analysis.sector_regime));
  const sector = firstText(context.sector, analysis.sector_v4);
  const blockers = humanBlockers(firstText(risk.decision_block_reasons_v5, analysis.decision_block_reasons_v5, risk.execution_block_reasons_v7));
  const publicGate = humanState(firstText(release.public_gate));
  const asOf = textValue(context.as_of_date) || textValue(objectValue(context.freshness).as_of_date);

  const watchLike = /WATCH|THEO DOI|KHONG HANH DONG|RESEARCH READY WATCH/i.test(`${setup} ${radarStatus} ${newPositionState}`);
  const q = question.toLowerCase();
  const asksHolding = /(đang giữ|đang nắm|nắm giữ|dang giu|dang nam|nam giu|bán|ban|giữ|giu|giá vốn|gia von)/i.test(q);

  let conclusion: string;
  if (watchLike) conclusion = `${ticker} hiện **chưa phù hợp mua mới**; trạng thái nghiên cứu là ${setup || newPositionState || "WATCH"}${price !== null ? ` tại ${fmtPrice(price)}` : ""}.`;
  else if (newPositionState) conclusion = `${ticker}: trạng thái mua mới hiện là **${newPositionState}**${price !== null ? ` tại ${fmtPrice(price)}` : ""}.`;
  else conclusion = `${ticker}${price !== null ? ` đang ở ${fmtPrice(price)}` : ""}; chưa có Action Report đủ điều kiện để phát hành lệnh giao dịch chính thức.`;

  const lines: string[] = [`**Kết luận:** ${conclusion}`];

  const buyBits: string[] = [];
  if (newPositionState) buyBits.push(humanState(newPositionState));
  if (setup) buyBits.push(`setup ${setup}`);
  if (radarScore !== null) buyBits.push(`Radar ${fmtNumber(radarScore, 1)}/100`);
  if (technicalScore !== null) buyBits.push(`kỹ thuật ${fmtNumber(technicalScore, 1)}/100`);
  if (flowScore !== null) buyBits.push(`dòng tiền ${fmtNumber(flowScore, 1)}/100 (${scoreLabel(flowScore)})`);
  if (rvol !== null) buyBits.push(`RVOL ${fmtNumber(rvol, 2)}x`);
  if (pivot !== null) buyBits.push(`pivot ${fmtPrice(pivot)}${pivotDistance !== null ? `, giá đang ${pivotDistance < 0 ? "dưới" : "trên"} ${fmtPct(Math.abs(pivotDistance), 1)}` : ""}`);
  lines.push(`**Mua mới:** ${watchLike ? "CHỜ / THEO DÕI" : (newPositionState || "chưa có tín hiệu hành động đã xác nhận")}${buyBits.length ? ` — ${buyBits.join(" · ")}` : ""}.`);

  if (holdingState && (asksHolding || holdingState)) {
    lines.push(`**Nếu đang nắm giữ:** ${holdingState}${holdingState.includes("GIU") || holdingState.includes("GIỮ") ? " — ưu tiên giữ/quan sát, chưa coi đây là tín hiệu bán chính thức." : "."}`);
  }

  const why: string[] = [];
  if (fundamentalScore !== null || valuationScore !== null) {
    const bits: string[] = [];
    if (fundamentalScore !== null) bits.push(`cơ bản ${fmtNumber(fundamentalScore, 1)}/100 (${scoreLabel(fundamentalScore)})`);
    if (valuationScore !== null) bits.push(`định giá ${fmtNumber(valuationScore, 1)}/100 (${scoreLabel(valuationScore)})`);
    why.push(bits.join(", "));
  }
  if (supplyDemandScore !== null) why.push(`cung-cầu ${fmtNumber(supplyDemandScore, 1)}/100 (${scoreLabel(supplyDemandScore)})`);
  if (riskScore !== null || marketScore !== null) {
    const bits: string[] = [];
    if (riskScore !== null) bits.push(`risk score ${fmtNumber(riskScore, 1)}`);
    if (marketScore !== null) bits.push(`market score ${fmtNumber(marketScore, 1)}/100`);
    why.push(bits.join(", "));
  }
  if (marketRegime || sectorRegime || sector) {
    why.push([marketRegime ? `thị trường ${marketRegime}` : "", sector ? `ngành ${sector}` : "", sectorRegime ? `regime ngành ${sectorRegime}` : ""].filter(Boolean).join(" · "));
  }
  if (why.length) lines.push(`**Vì sao:** ${why.slice(0, 4).join("; ")}.`);

  const trendBits: string[] = [];
  if (stage) trendBits.push(`Stage ${stage}`);
  if (ma10 !== null) trendBits.push(`MA10 ${fmtPrice(ma10)}`);
  if (ma50 !== null) trendBits.push(`MA50 ${fmtPrice(ma50)}`);
  if (ma150 !== null) trendBits.push(`MA150 ${fmtPrice(ma150)}`);
  if (ma200 !== null) trendBits.push(`MA200 ${fmtPrice(ma200)}`);
  if (technical.ichimoku_state) trendBits.push(`Ichimoku ${humanState(technical.ichimoku_state)}`);
  if (trendBits.length) lines.push(`**SEPA/Stage:** ${trendBits.join(" · ")}.`);

  const fundamentalBits: string[] = [];
  if (roe !== null) fundamentalBits.push(`ROE ${fmtPct(roe, 1)}`);
  if (revenueGrowth !== null) fundamentalBits.push(`doanh thu YoY ${fmtPct(revenueGrowth, 1)}`);
  if (profitGrowth !== null) fundamentalBits.push(`lợi nhuận YoY ${fmtPct(profitGrowth, 1)}`);
  if (pe !== null) fundamentalBits.push(`P/E ${fmtNumber(pe, 2)}x`);
  if (pb !== null) fundamentalBits.push(`P/B ${fmtNumber(pb, 2)}x`);
  if (fundamentalBits.length) lines.push(`**Cơ bản/định giá:** ${fundamentalBits.join(" · ")}.`);

  const valuationBits: string[] = [];
  if (fvBear !== null) valuationBits.push(`Bear ${fmtPrice(fvBear)}`);
  if (fvBase !== null) valuationBits.push(`Base ${fmtPrice(fvBase)}${upsideBase !== null ? ` (${fmtPct(upsideBase, 1)})` : ""}`);
  if (fvBull !== null) valuationBits.push(`Bull ${fmtPrice(fvBull)}`);
  if (research3To6m !== null) valuationBits.push(`mốc nghiên cứu 3–6T ${fmtPrice(research3To6m)}${price !== null ? ` (${fmtPct(pctFromTo(price, research3To6m), 1)})` : ""}`);
  if (research12m !== null) valuationBits.push(`mốc nghiên cứu 12T ${fmtPrice(research12m)}${price !== null ? ` (${fmtPct(pctFromTo(price, research12m), 1)})` : ""}`);
  if (rr !== null) valuationBits.push(`R/R nghiên cứu ${fmtNumber(rr, 2)}`);
  if (valuationBits.length) lines.push(`**Định giá/kỳ vọng nghiên cứu:** ${valuationBits.join(" · ")}. Các mốc này không phải Target hành động đã phát hành.`);

  const riskBits = blockers.slice(0, 5);
  if (catalyst.official_verified_v3 === true && catalyst.latest_official_title_v3) {
    riskBits.push(`catalyst HOSE gần nhất đã xác minh: ${textValue(catalyst.latest_official_title_v3)}`);
  }
  if (riskBits.length) lines.push(`**Rủi ro/điều kiện chặn:** ${riskBits.join("; ")}.`);
  else if (publicGate) lines.push(`**Điều kiện phát hành:** ${publicGate}.`);

  lines.push(`_Góc nhìn nghiên cứu — chưa phải khuyến nghị hành động đã xác nhận.${asOf ? ` Dữ liệu: ${asOf}.` : ""}_`);
  return lines.join("\n\n");
}

function portfolioResearchAnswer(contexts: JsonObject[]): string {
  const rows = contexts.slice(0, 12).map(context => {
    const ticker = textValue(context.ticker) || "—";
    const quote = objectValue(context.quote);
    const setup = objectValue(context.setup);
    const scores = objectValue(context.scores);
    const analysis = objectValue(context.analysis);
    const price = firstNumber(quote.price, analysis.price);
    const setupState = humanState(firstText(setup.candidate_setup, analysis.candidate_setup, setup.radar_status_v7));
    const newState = humanState(firstText(setup.new_position_state_v5, analysis.new_position_state_v5));
    const radar = firstNumber(scores.radar_score_v7, analysis.radar_score_v7);
    const flow = firstNumber(scores.flow_score_v4, analysis.flow_score_v4);
    return `- **${ticker}**: ${price !== null ? fmtPrice(price) : "chưa có giá"}${setupState ? ` · ${setupState}` : ""}${newState ? ` · ${newState}` : ""}${radar !== null ? ` · Radar ${fmtNumber(radar, 1)}` : ""}${flow !== null ? ` · dòng tiền ${fmtNumber(flow, 1)}` : ""}`;
  });
  return `**Kết luận:** Danh mục/watchlist đã có dữ liệu nghiên cứu; ưu tiên các mã có setup và dòng tiền xác nhận, còn mã ở WATCH/THEO DÕI thì chưa mở vị thế mới.\n\n${rows.join("\n")}\n\n_Góc nhìn nghiên cứu — chưa phải khuyến nghị hành động đã xác nhận. Chỉ phát hành MUA/BÁN, Buy Zone, Stop và Target chính thức khi Action Gate của từng mã READY._`;
}

export function deterministicStockRadarAnswer(args: {
  mode: StockRadarMode;
  researchContext?: JsonObject | JsonObject[] | null;
  actionContext?: JsonObject[] | null;
  question?: string;
}): string {
  const researchRows = Array.isArray(args.researchContext)
    ? args.researchContext.filter(Boolean)
    : args.researchContext ? [args.researchContext] : [];

  if (args.mode === "RESEARCH_ONLY" && researchRows.length === 1) {
    return singleResearchAnswer(researchRows[0], args.question || "");
  }
  if (args.mode === "RESEARCH_ONLY" && researchRows.length > 1) {
    return portfolioResearchAnswer(researchRows);
  }
  if (args.mode === "ACTION_READY" && args.actionContext?.length) {
    return "**Kết luận:** Action Report của StockRadar đã READY nhưng lớp diễn giải AI đang tạm gián đoạn. Hãy dùng trực tiếp Buy Zone, Stop, Target và trạng thái đã phát hành trong Action Report; hệ thống không tự tạo thêm số ngoài dữ liệu đã xác nhận.";
  }
  return "**Kết luận:** StockRadar chưa có đủ dữ liệu hiện tại cho mã này để đưa ra nhận định đáng tin cậy. Cần thêm dữ liệu giá/volume, cấu trúc nền-pivot và dữ liệu cơ bản đủ mới; hệ thống không dùng tín hiệu cũ để bù vào phần còn thiếu.";
}
