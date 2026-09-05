function obj(value: any): Record<string, any> { return value && typeof value === 'object' && !Array.isArray(value) ? value : {}; }
function num(value: any): number | null { if (value === null || value === undefined || value === '') return null; const n = Number(value); return Number.isFinite(n) ? n : null; }
function txt(value: any): string { return typeof value === 'string' ? value.trim() : value == null ? '' : String(value).trim(); }
function fmtNumber(value: any, digits = 2): string { const n = num(value); return n == null ? '' : n.toLocaleString('vi-VN', { maximumFractionDigits: digits }); }
function fmtPrice(value: any): string { const n = num(value); return n == null ? '' : `${Math.round(n).toLocaleString('vi-VN')}đ`; }
function fmtPct(value: any, digits = 1): string { const n = num(value); return n == null ? '' : `${n.toLocaleString('vi-VN', { maximumFractionDigits: digits })}%`; }
function pctFrom(price: any, target: any): number | null { const p = num(price), t = num(target); return p && t != null ? ((t / p) - 1) * 100 : null; }
function firstNum(...values: any[]): number | null { for (const value of values) { const n = num(value); if (n != null) return n; } return null; }
function firstTxt(...values: any[]): string { for (const value of values) { const s = txt(value); if (s) return s; } return ''; }
function dateVi(value: any): string { const s = txt(value).slice(0, 10); const m = s.match(/^(\d{4})-(\d{2})-(\d{2})$/); return m ? `${m[3]}/${m[2]}/${m[1]}` : txt(value); }
function state(value: any): string {
  const s = txt(value).replaceAll('_', ' ').replace(/\s+/g, ' ').trim();
  const exact: Record<string,string> = {
    WATCH:'THEO DÕI', 'THEO DOI':'THEO DÕI', 'THEO DOI KHONG HANH DONG':'THEO DÕI — CHƯA HÀNH ĐỘNG',
    'KHONG HANH DONG':'CHƯA HÀNH ĐỘNG', 'HA TY TRONG HOAC BAN':'HẠ TỶ TRỌNG HOẶC BÁN', GIU:'GIỮ',
    'GIU QUAN SAT':'GIỮ VÀ QUAN SÁT', 'PHAN HOA THAN TRONG':'PHÂN HÓA, THẬN TRỌNG', LAGGING:'YẾU HƠN THỊ TRƯỜNG',
    LEADING:'DẪN DẮT', WEAK:'YẾU', NEUTRAL:'TRUNG TÍNH', STRONG:'MẠNH', 'CONFIRMED BREAKOUT':'BREAKOUT XÁC NHẬN',
    'EARLY BREAKOUT':'EARLY BREAKOUT', 'POCKET PIVOT':'POCKET PIVOT', 'RESEARCH READY WATCH':'THEO DÕI — DỮ LIỆU NGHIÊN CỨU SẴN SÀNG'
  };
  return exact[s.toUpperCase()] || s;
}
const REASONS: Record<string,string> = {
  NO_BUY_SETUP:'chưa có setup mua đạt chuẩn', MISSING_ACTION_MAP:'chưa có bản đồ hành động đủ điều kiện phát hành',
  UPSIDE_TOO_LOW:'dư địa tăng tại điểm vào hiện tại chưa đủ hấp dẫn', RR_BELOW_2:'Risk/Reward dưới 2',
  CURRENT_CORPORATE_ACTION_UNVERIFIED:'cần xác minh thêm sự kiện/quyền doanh nghiệp hiện tại',
  RESEARCH_OR_DATA_GATE_NOT_READY:'dữ liệu nghiên cứu chưa đạt chuẩn', SCAN_SLA_NOT_READY:'dữ liệu quét trong phiên chưa đạt SLA',
  AUTHORITATIVE_CORPORATE_ACTION_SOURCE_UNAVAILABLE:'nguồn sự kiện/quyền doanh nghiệp chính thức chưa sẵn sàng'
};
function blockerText(value: any, corporateActionClear = false): string {
  const raw = Array.isArray(value) ? value : txt(value).split('|');
  return raw.map(txt).filter(Boolean).filter(v => !(corporateActionClear && v === 'CURRENT_CORPORATE_ACTION_UNVERIFIED')).map(v => REASONS[v] || state(v)).join('; ');
}
function pushMetric(list: string[], label: string, value: any, kind: 'number'|'pct'|'price'|'multiple' = 'number', digits = 1) {
  const n = num(value); if (n == null) return;
  const formatted = kind === 'pct' ? fmtPct(n, digits) : kind === 'price' ? fmtPrice(n) : kind === 'multiple' ? `${fmtNumber(n,digits)}x` : fmtNumber(n,digits);
  list.push(`${label} ${formatted}`);
}

export function buildResearchSnapshot(context: any): any {
  if (!context) return null;
  const a=obj(context.analysis), tech=obj(context.technical_detail), post=obj(context.scanner_postclose), val=obj(context.valuation_detail), fund=obj(context.fundamental_detail), plan=obj(context.trade_plan), scores=obj(context.scores), risk=obj(context.risk), market=obj(context.market_context), supply=obj(context.supply_institutional), catalyst=obj(context.catalyst), corp=obj(context.corporate_action), quote=obj(context.quote), setup=obj(context.setup);
  const price=firstNum(quote.price,a.price,post.price);
  const targetNear=firstNum(plan.target_near,a.target_near_rr2_v5), target36=firstNum(plan.target_3_6m,a.target_3_6m_v5), target12=firstNum(plan.target_12m,a.target_12m_v5);
  const corporateActionClear=corp.execution_clear_v7===true || corp.gate_v2==='PASS_NO_NEAR_SENSITIVE_EVENT';
  return {
    ticker:txt(context.ticker), context_grade:txt(context.context_grade), as_of_date:txt(context.as_of_date), generated_at:txt(context.generated_at), sector:txt(context.sector), company_type:txt(context.company_type), price,
    setup:{
      candidate_setup:state(firstTxt(setup.candidate_setup,a.candidate_setup,post.candidate_setup,post.setup_internal,a.radar_status_v7,a.radar_status_v6)),
      radar_status:state(firstTxt(setup.radar_status_v7,a.radar_status_v7,a.radar_status_v6)),
      new_position_state:state(firstTxt(setup.new_position_state_v5,a.new_position_state_v5)),
      holding_state:state(firstTxt(setup.holding_state_v5,a.holding_state_v5)),
      stage:state(firstTxt(tech.stage,tech.stage_analysis,tech.stage_label,a.stage,a.stage_analysis)),
      pivot:firstNum(tech.pivot20,tech.pivot,post.pivot20,post.pivot), distance_to_pivot_pct:firstNum(tech.distance_to_pivot_pct,post.distance_to_pivot_pct),
      rvol:firstNum(tech.rvol_progress_adjusted,tech.rvol,post.rvol_progress_adjusted,post.rvol), pocket_pivot_volume_pass:tech.pocket_pivot_volume_pass ?? post.pocket_pivot_volume_pass ?? null,
      ma10:firstNum(tech.ma10,a.ma10,post.ma10), ma50:firstNum(tech.ma50,a.ma50,post.ma50), ma150:firstNum(tech.ma150,a.ma150,post.ma150), ma200:firstNum(tech.ma200,a.ma200,post.ma200),
      volume:firstNum(tech.volume,post.volume,a.volume), vol20:firstNum(tech.vol20,tech.volume20,post.vol20,post.volume20,a.vol20), max_down_volume10:firstNum(tech.max_down_volume10,post.max_down_volume10,a.max_down_volume10),
      bollinger: firstTxt(tech.bollinger_state,tech.bollinger,post.bollinger_state), ichimoku:firstTxt(tech.ichimoku_state,tech.ichimoku,post.ichimoku_state)
    },
    scores:{
      radar:firstNum(scores.radar_score_v7,a.radar_score_v7,a.radar_score_v6), fundamental:firstNum(scores.fundamental_domain_score_v4,a.fundamental_domain_score_v4), valuation:firstNum(scores.valuation_domain_score_v4,a.valuation_domain_score_v4), technical:firstNum(scores.technical_score,a.technical_score), flow:firstNum(scores.flow_score_v4,a.flow_score_v4), supply_demand:firstNum(scores.supply_demand_score_v1,a.supply_demand_score_v1), liquidity:firstNum(scores.liquidity_score_v4,a.liquidity_score_v4), sector_strength:firstNum(scores.sector_strength_score,a.sector_strength_score), market:firstNum(scores.market_score,a.market_score), risk:firstNum(scores.risk_score,a.risk_score)
    },
    fundamentals:{
      revenue_growth_yoy_pct:firstNum(fund.revenue_growth_yoy_pct,fund.revenue_yoy_pct,a.revenue_growth_yoy_pct), profit_growth_yoy_pct:firstNum(fund.profit_growth_yoy_pct,fund.net_profit_yoy_pct,a.profit_growth_yoy_pct), eps_growth_yoy_pct:firstNum(fund.eps_growth_yoy_pct,a.eps_growth_yoy_pct), roe_pct:firstNum(fund.roe_pct,fund.roe,a.roe_pct), roa_pct:firstNum(fund.roa_pct,fund.roa,a.roa_pct), net_margin_pct:firstNum(fund.net_margin_pct,a.net_margin_pct), debt_to_equity:firstNum(fund.debt_to_equity,a.debt_to_equity), fundamental_confidence:firstNum(fund.fundamental_confidence_v4,a.fundamental_confidence_v4)
    },
    valuation:{
      pe:firstNum(val.pe,val.trailing_pe,a.pe), forward_pe:firstNum(val.forward_pe,a.forward_pe), pb:firstNum(val.pb,val.p_b,a.pb), peg:firstNum(val.peg,a.peg), ev_ebitda:firstNum(val.ev_ebitda,a.ev_ebitda), fair_value:firstNum(val.fair_value,val.base_fair_value,a.fair_value), valuation_confidence:firstNum(val.valuation_score_confidence_v4,a.valuation_score_confidence_v4)
    },
    trade_plan:{
      buy_zone_low:firstNum(plan.buy_zone_low,a.buy_zone_low_v5), buy_zone_high:firstNum(plan.buy_zone_high,a.buy_zone_high_v5), position_initial_pct:firstNum(plan.position_initial_pct,a.position_initial_pct_v5), stop_loss:firstNum(plan.stop_loss,a.stop_loss_v5), downside_to_stop_pct:firstNum(plan.downside_to_stop_pct,a.downside_to_stop_pct_v5), target_near:targetNear, target_3_6m:target36, target_12m:target12, target_near_upside_pct:pctFrom(price,targetNear), target_3_6m_upside_pct:pctFrom(price,target36), target_12m_upside_pct:pctFrom(price,target12), risk_reward_to_base:firstNum(plan.risk_reward_to_base,a.rr_to_base_v5)
    },
    risk:{atr20_pct:firstNum(risk.atr20_pct,a.atr20_pct), realized_vol20_pct:firstNum(risk.realized_vol20_pct,a.realized_vol20_pct), max_drawdown60_pct:firstNum(risk.max_drawdown60_pct,a.max_drawdown60_pct), blockers:blockerText(a.decision_block_reasons_v5 || risk.decision_block_reasons_v5 || risk.execution_block_reasons_v7,corporateActionClear)},
    market:{market_regime:state(firstTxt(market.market_regime,a.market_regime)), sector_regime:state(firstTxt(market.sector_regime,a.sector_regime))},
    supply_institutional:{free_float_proxy_pct:firstNum(supply.free_float_proxy_pct,a.free_float_proxy_pct), float_turnover20_pct:firstNum(supply.float_turnover20_pct,a.float_turnover20_pct), context_ready:supply.institutional_context_ready===true},
    catalyst:{official_verified:catalyst.official_verified_v3===true || catalyst.catalyst_official_verified_v3===true, official_items_30d:firstNum(catalyst.official_items_30d_v3,a.official_items_30d_v3), official_items_90d:firstNum(catalyst.official_items_90d_v3,a.official_items_90d_v3), latest_time:firstTxt(catalyst.latest_official_time_v3,catalyst.latest_official_time,a.latest_official_catalyst_time_v3,a.latest_catalyst_time_v2), latest_title:firstTxt(catalyst.latest_official_title_v3,catalyst.latest_official_title,a.latest_official_catalyst_title_v3,a.latest_catalyst_title_v2).slice(0,260)},
    corporate_action:{review_required:corp.review_required_v2===true, next_record_date:txt(corp.next_sensitive_record_date_v2), next_event_type:txt(corp.next_sensitive_event_type_v2), next_event_title:txt(corp.next_sensitive_event_title_v2).slice(0,200)},
    coverage:{factor_coverage_pct:firstNum(scores.factor_coverage_pct_v6,a.factor_coverage_pct_v6), decision_confidence:firstNum(scores.decision_confidence_v5,a.decision_confidence_v5)}
  };
}

export function researchSnapshotText(context: any): string {
  const x=buildResearchSnapshot(context); if(!x) return '';
  const reference=x.context_grade!=='RESEARCH_READY';
  const lines=[`DỮ LIỆU NGHIÊN CỨU STOCKRADAR — ${x.ticker}${reference?' (THAM CHIẾU)':''}`];
  const meta:string[]=[]; pushMetric(meta,'Giá',x.price,'price'); if(x.as_of_date)meta.push(`ngày ${dateVi(x.as_of_date)}`); if(x.sector)meta.push(`ngành ${x.sector}`); if(meta.length)lines.push(`- Giá / bối cảnh: ${meta.join(' · ')}.`);
  const states:string[]=[]; if(x.setup.candidate_setup)states.push(`setup ${x.setup.candidate_setup}`); if(x.setup.new_position_state)states.push(`mua mới ${x.setup.new_position_state}`); if(x.setup.holding_state)states.push(`nắm giữ ${x.setup.holding_state}`); if(x.setup.stage)states.push(`Stage ${x.setup.stage}`); if(states.length)lines.push(`- Trạng thái: ${states.join(' · ')}.`);
  const technical:string[]=[]; pushMetric(technical,'Pivot',x.setup.pivot,'price'); pushMetric(technical,'cách pivot',x.setup.distance_to_pivot_pct,'pct'); pushMetric(technical,'RVOL',x.setup.rvol,'multiple',2); pushMetric(technical,'MA10',x.setup.ma10,'price'); pushMetric(technical,'MA50',x.setup.ma50,'price'); pushMetric(technical,'MA150',x.setup.ma150,'price'); pushMetric(technical,'MA200',x.setup.ma200,'price'); if(x.setup.pocket_pivot_volume_pass!==null)technical.push(`Pocket Pivot volume ${x.setup.pocket_pivot_volume_pass===true?'đạt':'chưa đạt'}`); if(x.setup.bollinger)technical.push(`Bollinger ${x.setup.bollinger}`); if(x.setup.ichimoku)technical.push(`Ichimoku ${x.setup.ichimoku}`); if(technical.length)lines.push(`- Kỹ thuật chi tiết: ${technical.join(' · ')}.`);
  const volumes:string[]=[]; pushMetric(volumes,'Volume',x.setup.volume,'number',0); pushMetric(volumes,'Vol20',x.setup.vol20,'number',0); pushMetric(volumes,'Max down-volume 10 phiên',x.setup.max_down_volume10,'number',0); if(volumes.length)lines.push(`- Khối lượng: ${volumes.join(' · ')}.`);
  const scoreBits:string[]=[]; for(const [label,value] of [['Radar',x.scores.radar],['Cơ bản',x.scores.fundamental],['Định giá',x.scores.valuation],['Kỹ thuật',x.scores.technical],['Dòng tiền',x.scores.flow],['Cung/cầu',x.scores.supply_demand],['Thanh khoản',x.scores.liquidity],['Sức mạnh ngành',x.scores.sector_strength],['Thị trường',x.scores.market],['Rủi ro',x.scores.risk]] as any[])pushMetric(scoreBits,label,value,'number',1); if(scoreBits.length)lines.push(`- Bộ điểm: ${scoreBits.map(v=>`${v}/100`).join(' · ')}.`);
  const fundBits:string[]=[]; pushMetric(fundBits,'Doanh thu YoY',x.fundamentals.revenue_growth_yoy_pct,'pct'); pushMetric(fundBits,'LN YoY',x.fundamentals.profit_growth_yoy_pct,'pct'); pushMetric(fundBits,'EPS YoY',x.fundamentals.eps_growth_yoy_pct,'pct'); pushMetric(fundBits,'ROE',x.fundamentals.roe_pct,'pct'); pushMetric(fundBits,'ROA',x.fundamentals.roa_pct,'pct'); pushMetric(fundBits,'Biên LN',x.fundamentals.net_margin_pct,'pct'); pushMetric(fundBits,'D/E',x.fundamentals.debt_to_equity,'multiple'); if(fundBits.length)lines.push(`- Cơ bản: ${fundBits.join(' · ')}.`);
  const valBits:string[]=[]; pushMetric(valBits,'P/E',x.valuation.pe,'multiple'); pushMetric(valBits,'Forward P/E',x.valuation.forward_pe,'multiple'); pushMetric(valBits,'P/B',x.valuation.pb,'multiple'); pushMetric(valBits,'PEG',x.valuation.peg,'multiple'); pushMetric(valBits,'EV/EBITDA',x.valuation.ev_ebitda,'multiple'); pushMetric(valBits,'Fair Value',x.valuation.fair_value,'price'); if(valBits.length)lines.push(`- Định giá: ${valBits.join(' · ')}.`);
  const plan:string[]=[]; const low=num(x.trade_plan.buy_zone_low),high=num(x.trade_plan.buy_zone_high); plan.push(low!=null||high!=null?`Buy Zone ${low!=null?fmtPrice(low):'—'}–${high!=null?fmtPrice(high):'—'}`:'Buy Zone chưa có'); if(num(x.trade_plan.stop_loss)!=null)plan.push(`Stop ${fmtPrice(x.trade_plan.stop_loss)}${num(x.trade_plan.downside_to_stop_pct)!=null?` (${fmtPct(x.trade_plan.downside_to_stop_pct)})`:''}`); else plan.push('Stop chưa có'); for(const [label,value,upside] of [['Target gần',x.trade_plan.target_near,x.trade_plan.target_near_upside_pct],['Target 3–6 tháng',x.trade_plan.target_3_6m,x.trade_plan.target_3_6m_upside_pct],['Target 12 tháng',x.trade_plan.target_12m,x.trade_plan.target_12m_upside_pct]] as any[]){if(num(value)!=null)plan.push(`${label} ${fmtPrice(value)}${num(upside)!=null?` (${num(upside)>=0?'+':''}${fmtPct(upside)})`:''}`);} if(num(x.trade_plan.risk_reward_to_base)!=null)plan.push(`R/R ${fmtNumber(x.trade_plan.risk_reward_to_base,2)}`); if(num(x.trade_plan.position_initial_pct)!=null)plan.push(`tỷ trọng khởi đầu ${fmtPct(x.trade_plan.position_initial_pct)}`); lines.push(`- Kế hoạch nghiên cứu: ${plan.join(' · ')}.`);
  const riskBits:string[]=[]; pushMetric(riskBits,'ATR20',x.risk.atr20_pct,'pct',2); pushMetric(riskBits,'biến động 20 phiên',x.risk.realized_vol20_pct,'pct',2); pushMetric(riskBits,'drawdown 60 phiên',x.risk.max_drawdown60_pct,'pct',2); if(riskBits.length)lines.push(`- Biến động / rủi ro: ${riskBits.join(' · ')}.`);
  const marketBits:string[]=[]; if(x.market.market_regime)marketBits.push(`thị trường ${x.market.market_regime}`); if(x.market.sector_regime)marketBits.push(`ngành ${x.market.sector_regime}`); if(marketBits.length)lines.push(`- Market Direction: ${marketBits.join(' · ')}.`);
  const supplyBits:string[]=[]; pushMetric(supplyBits,'free-float proxy',x.supply_institutional.free_float_proxy_pct,'pct'); pushMetric(supplyBits,'turnover20',x.supply_institutional.float_turnover20_pct,'pct',2); if(supplyBits.length)lines.push(`- Cung / tổ chức: ${supplyBits.join(' · ')}.`);
  const catalystBits:string[]=[]; if(num(x.catalyst.official_items_30d)!=null)catalystBits.push(`${fmtNumber(x.catalyst.official_items_30d,0)} tin HOSE/30 ngày`); if(num(x.catalyst.official_items_90d)!=null)catalystBits.push(`${fmtNumber(x.catalyst.official_items_90d,0)} tin/90 ngày`); if(x.catalyst.latest_title)catalystBits.push(`mới nhất: ${x.catalyst.latest_title}${x.catalyst.latest_time?` (${x.catalyst.latest_time})`:''}`); if(catalystBits.length)lines.push(`- Catalyst chính thức: ${catalystBits.join(' · ')}.`);
  const quality:string[]=[]; pushMetric(quality,'độ phủ',x.coverage.factor_coverage_pct,'pct'); pushMetric(quality,'độ tin cậy quyết định',x.coverage.decision_confidence,'pct'); pushMetric(quality,'độ tin cậy cơ bản',x.fundamentals.fundamental_confidence,'pct'); pushMetric(quality,'độ tin cậy định giá',x.valuation.valuation_confidence,'pct'); if(quality.length)lines.push(`- Chất lượng dữ liệu: ${quality.join(' · ')}.`);
  if(x.corporate_action.review_required||x.corporate_action.next_event_title||x.corporate_action.next_record_date){const ca:string[]=[]; if(x.corporate_action.review_required)ca.push('cần rà soát sự kiện doanh nghiệp'); if(x.corporate_action.next_event_title)ca.push(x.corporate_action.next_event_title); if(x.corporate_action.next_record_date)ca.push(`ngày chốt ${dateVi(x.corporate_action.next_record_date)}`); lines.push(`- Sự kiện doanh nghiệp: ${ca.join(' · ')}.`);}
  if(x.risk.blockers)lines.push(`- Điểm chặn hiện tại: ${x.risk.blockers}.`);
  lines.push(reference?'- Mức dữ liệu: tham chiếu; chưa đạt research-ready, không dùng như tín hiệu hành động.':'- Mức dữ liệu: research-ready; dữ liệu nghiên cứu không thay thế Action Report khi hệ thống phát hành tín hiệu chính thức.');
  return lines.join('\n');
}

export function appendResearchSnapshot(answer: string, context: any): string {
  const base=txt(answer); if(!base||!context||base.includes('DỮ LIỆU NGHIÊN CỨU STOCKRADAR')) return base;
  const block=researchSnapshotText(context); return block?`${base}\n\n${block}`:base;
}
