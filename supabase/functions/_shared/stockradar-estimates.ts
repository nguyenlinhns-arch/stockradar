// Research scenarios, never approval, an executable order, or a verified forecast.
type Data = Record<string, any>;
const obj = (v: any): Data => v && typeof v === 'object' && !Array.isArray(v) ? v : {};
const num = (v: any): number | null => v == null || typeof v === 'boolean' || typeof v === 'object' || String(v).trim() === '' ? null : Number.isFinite(Number(v)) ? Number(v) : null;
const positive = (v: any) => { const x = num(v); return x != null && x > 0 ? x : null; };
const money = (v: any) => positive(v) == null ? 'chưa đủ dữ liệu' : `${Math.round(v).toLocaleString('vi-VN')}đ`;
const percent = (v: number) => `${v.toLocaleString('vi-VN', {maximumFractionDigits: 1})}%`;

export function researchEstimates(c: Data): Data {
  const empty = {schema_version: 'STOCKRADAR_ESTIMATES_V1', status: 'INSUFFICIENT_DATA', public_action_allowed: false, short_term: null, medium_term: null, long_term: null, accumulation: null};
  const quality = String(c.data_quality || '').toUpperCase();
  const snapshotStatus = String(c.price_snapshot_status || '').toUpperCase();
  if (c.context_grade !== 'RESEARCH_READY' || /STALE|ERROR|INVALID|FAILED/.test(quality + snapshotStatus)) return empty;
  const quote = obj(c.quote), t = obj(c.technical_detail), i = obj(t.computed_indicators), f = obj(c.fundamental_detail);
  const price = positive(quote.price ?? t.price);
  if (price == null) return empty;
  const result: Data = {...empty, as_of_date: c.as_of_date, snapshot_id: c.snapshot_id, price, confidence: 'LOW', assumptions_verified: false, not_a_buy_signal: true};
  const pivot = positive(i.pivot20 ?? t.pivot20 ?? t.pivot);
  const atr = positive(i.atr20_pct ?? t.atr20_pct ?? obj(c.risk).atr20_pct);
  // Match the existing decision engine's risk policy, without inventing missing ATR.
  if (pivot != null && atr != null && price <= pivot * 1.025) {
    const lossPct = Math.min(8, Math.max(5, 1.5 * atr));
    const stop = pivot * (1 - lossPct / 100);
    result.short_term = {entry: pivot, stop_loss: stop, target: pivot + 2 * (pivot - stop), risk_reward: 2, atr20_pct: atr, loss_pct: lossPct,
      method: 'ENTRY_PLUS_2R_ATR_STOP', condition: 'Chỉ áp dụng nếu điểm mua quanh mốc theo dõi được xác nhận; chạm giá chưa đủ để mua. Đây là mức quản trị vốn, không phải dự báo khả năng đạt giá.'};
  }
  // Explicit model assumptions. Do not copy historical base/bull values into horizons.
  // Financial firms use book value; other firms require positive trailing EPS.
  const bookModel = ['BANK', 'SECURITIES', 'INSURANCE'].includes(String(c.business_bucket));
  const input = positive(bookModel ? f.bvps : f.eps_ttm ?? f.eps);
  const multiple = positive(bookModel ? f.pb_median_8q_provider : f.pe_median_8q_provider);
  const period = String(f.period_end || '');
  const observationMonth = String(c.as_of_date || '').slice(0,7).replace('-', '');
  if (input != null && multiple != null && /^\d{6}$/.test(period) && period <= observationMonth) {
    let growth: number | null = bookModel ? num(f.equity_growth_yoy_pct) : num(f.eps_growth_yoy_pct);
    let growthSource = bookModel ? 'tăng trưởng vốn chủ sở hữu, giả định số cổ phiếu không đổi' : 'tăng trưởng lợi nhuận mỗi cổ phiếu gần nhất';
    if (!bookModel && growth == null) {
      const revenue = [num(f.revenue_growth_yoy_pct), num(f.revenue_growth_3y_avg_pct)].filter((v): v is number => v != null);
      growth = revenue.length ? Math.min(...revenue) : null;
      growthSource = revenue.length ? 'tăng trưởng doanh thu thấp hơn trong các kỳ có dữ liệu, giả định biên lợi nhuận và số cổ phiếu không đổi' : 'kịch bản tăng trưởng bằng 0 do thiếu dự báo';
    }
    if (growth == null) growthSource = 'kịch bản tăng trưởng bằng 0 do thiếu dự báo';
    const observedGrowth = growth;
    // A declared scenario limit, not a source observation or a calibrated forecast.
    const annualGrowth = Math.max(-30, Math.min(20, growth ?? 0));
    const value = (months: number) => input * Math.pow(1 + annualGrowth / 100, months / 12) * multiple;
    const at3 = value(3), at6 = value(6), at12 = value(12);
    result.valuation_model = {method: bookModel ? 'PROJECTED_BVPS_X_HISTORICAL_PB' : 'PROJECTED_EPS_X_HISTORICAL_PE', input, multiple, annual_growth_pct: annualGrowth, observed_growth_pct: observedGrowth,
      growth_source: growthSource, period_end: f.period_end ?? null, multiple_period: '8 quý', growth_limit_pct: [-30, 20],
      formula: `${bookModel ? 'BVPS' : 'EPS'} × (1 + tăng trưởng giả định)^(số tháng/12) × ${bookModel ? 'P/B' : 'P/E'} lịch sử`};
    result.medium_term = {at_3_months: at3, at_6_months: at6, low: Math.min(at3, at6), high: Math.max(at3, at6), upside_at_6m_pct: (at6 / price - 1) * 100};
    result.long_term = {target: at12, upside_pct: (at12 / price - 1) * 100};
    result.accumulation = {price_ceiling: at12 * 0.8, model_margin_pct: 20,
      condition: 'Ngưỡng tham khảo bằng 80% kịch bản 12 tháng; chỉ xem xét sau khi kiểm chứng doanh nghiệp và giả định định giá. Không tự động là vùng mua tích sản.'};
  }
  result.status = result.short_term || result.medium_term ? 'MODEL_SCENARIO' : 'INSUFFICIENT_DATA';
  return result;
}

export function estimatedPlanText(c: Data): string {
  const e = researchEstimates(c);
  if (e.status !== 'MODEL_SCENARIO') return 'MỤC TIÊU DỰ KIẾN VÀ CẮT LỖ: Chưa đủ dữ liệu hiện tại để tính các mốc có căn cứ.';
  const lines = ['MỤC TIÊU DỰ KIẾN VÀ CẮT LỖ — kịch bản tham khảo, độ tin cậy thấp; chưa phải khuyến nghị mua:'];
  const s = e.short_term, m = e.medium_term, l = e.long_term, a = e.accumulation, v = e.valuation_model;
  lines.push(s ? `- Ngắn hạn: mục tiêu ${money(s.target)}; cắt lỗ ${money(s.stop_loss)} nếu giá vào giả định ${money(s.entry)} được xác nhận. Rủi ro ${percent(s.loss_pct)} từ giá vào, mục tiêu bằng 2 lần khoản rủi ro. ${s.condition}` : '- Ngắn hạn: chưa đủ mốc giá/độ biến động để tính mục tiêu và cắt lỗ.');
  lines.push(m ? `- 3–6 tháng: ${money(m.at_3_months)} ở mốc 3 tháng → ${money(m.at_6_months)} ở mốc 6 tháng (${percent(m.upside_at_6m_pct)} so với giá quan sát).` : '- 3–6 tháng: chưa đủ dữ liệu lợi nhuận hoặc giá trị sổ sách và hệ số định giá.');
  lines.push(l ? `- 12 tháng: ${money(l.target)} (${percent(l.upside_pct)} so với giá quan sát).` : '- 12 tháng: chưa đủ dữ liệu để tính kịch bản.');
  lines.push(a ? `- Tích sản: ngưỡng tham khảo tối đa ${money(a.price_ceiling)} với biên dự phòng mô hình 20%. ${a.condition}` : '- Tích sản: chưa xác định được ngưỡng giá có căn cứ.');
  if (v) lines.push(`Giả định định giá: ${v.formula}; đầu vào ${money(v.input)}, hệ số ${v.multiple.toLocaleString('vi-VN', {maximumFractionDigits: 2})} lần của ${v.multiple_period}; tăng trưởng giả định ${percent(v.annual_growth_pct)}/năm từ ${v.growth_source}. Mô hình giới hạn tăng trưởng trong −30% đến +20%/năm. Đây chưa phải dự báo đã kiểm chứng; chưa xét đầy đủ sự kiện làm thay đổi số cổ phiếu, lợi nhuận hoặc hệ số định giá.`);
  if (s) lines.push(`Căn cứ cắt lỗ ngắn hạn: 1,5 × biên độ dao động bình quân 20 phiên (${percent(s.atr20_pct)}), giới hạn mức lỗ 5–8%. Mức này chỉ áp dụng cho kế hoạch ngắn hạn, không dùng chung cho 3–6 tháng, 12 tháng hoặc tích sản. Khi có khuyến nghị chính thức, dùng cắt lỗ riêng của báo cáo theo thời hạn.`);
  return lines.join('\n');
}

// Insert the exact computed block immediately after the conclusion on both model
// and deterministic responses. The language model does not calculate these prices.
export function withEstimatedPlan(answer: string, context: Data): string {
  if (!context) return answer;
  const block = estimatedPlanText(context);
  if (answer.includes(block)) return answer;
  const parts = String(answer || '').split(/\n\s*\n/).filter(p => !p.startsWith('MỤC TIÊU DỰ KIẾN VÀ CẮT LỖ'));
  parts.splice(Math.min(1, parts.length), 0, block);
  return parts.join('\n\n');
}
