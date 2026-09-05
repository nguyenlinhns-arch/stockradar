import test from 'node:test';
import assert from 'node:assert/strict';
import {researchEstimates,estimatedPlanText,withEstimatedPlan} from '../../supabase/functions/_shared/stockradar-estimates.ts';
import {normalizeResearchContext,deterministicStockRadarAnswer} from '../../supabase/functions/_shared/stockradar-core.ts';
import {analysisContract,appendResearchSnapshot} from '../../supabase/functions/_shared/stockradar-research-view.ts';
import {emailPricePlanError,actionBody,dailyBody} from '../../supabase/functions/_shared/email-copy.ts';

const context=()=>({ticker:'MWG',context_grade:'RESEARCH_READY',as_of_date:'2026-09-04',data_quality:'updated',quote:{price:73100},business_bucket:'GENERAL',
  technical_detail:{pivot20:75900,computed_indicators:{atr20_pct:2.3803}},fundamental_detail:{period_end:'202606',eps_ttm:3955.55,pe_median_8q_provider:17.175,revenue_growth_yoy_pct:16.71,revenue_growth_3y_avg_pct:6.103333333333334,pbt_growth_yoy_pct:103.4}});
test('MWG scenarios retain a bearish valuation outcome and state revenue-to-EPS assumptions',()=>{
  const c=context(),e=researchEstimates(c);
  assert.equal(e.short_term.entry,75900);assert.equal(e.short_term.stop_loss,72105);assert.equal(e.short_term.target,83490);
  assert.equal(e.valuation_model.annual_growth_pct,6.103333333333334);
  assert.ok(e.long_term.target<73100,'never force upside when the model is below observed price');
  assert.ok(e.medium_term.at_3_months<e.medium_term.at_6_months && e.medium_term.at_6_months<e.long_term.target);
  assert.equal(e.public_action_allowed,false);assert.equal(e.assumptions_verified,false);
  assert.match(estimatedPlanText(c),/biên lợi nhuận và số cổ phiếu không đổi/);
  assert.doesNotMatch(estimatedPlanText(c),/103,4%/,'PBT growth cannot masquerade as EPS growth');
});
test('missing, stale, reference-only and future accounting inputs never create a numeric forecast',()=>{
  for(const extra of [{data_quality:'stale'},{data_quality:'error'},{context_grade:'REFERENCE_ONLY'},{quote:{price:null}},{price_snapshot_status:'INVALID'}]) assert.equal(researchEstimates({...context(),...extra}).status,'INSUFFICIENT_DATA');
  for(const bad of [null,false,'',0,-1,Infinity]) assert.equal(researchEstimates({...context(),fundamental_detail:{...context().fundamental_detail,eps_ttm:bad}}).long_term,null);
  assert.equal(researchEstimates({...context(),fundamental_detail:{...context().fundamental_detail,period_end:'202612'}}).long_term,null);
  assert.equal(researchEstimates({...context(),technical_detail:{pivot20:75900}}).short_term,null);
});
test('computed estimates sit immediately after conclusion and cannot promote official target fields',()=>{
  const raw={status:'INTERNAL_RESEARCH_READY',ticker:'MWG',as_of_date:'2026-09-04',payload:context()};
  const c=normalizeResearchContext(raw),a=analysisContract(c);
  assert.equal(a.targets.twelve_months,null);assert.equal(a.public_action_allowed,false);
  assert.equal(a.estimated_plan.status,'MODEL_SCENARIO');
  const answer=deterministicStockRadarAnswer({mode:'RESEARCH_ONLY',researchContext:c,question:'MWG 3–6 tháng'});
  assert.match(answer,/^KẾT LUẬN:[^\n]+\n\nMỤC TIÊU DỰ KIẾN VÀ CẮT LỖ/);
  assert.equal(withEstimatedPlan(answer,c),answer);
  const corrected=withEstimatedPlan('KẾT LUẬN: Theo dõi.\n\nMỤC TIÊU DỰ KIẾN VÀ CẮT LỖ: 999.999đ',c);
  assert.doesNotMatch(corrected,/999\.999/);assert.match(corrected,/83\.490đ/);
});
test('official root-level targets survive action contract and do not acquire a research scenario',()=>{
  const c=context(),r={status:'READY',ticker:'MWG',horizon:'LONG_TERM',payload:{stop_loss:70000,target_12m:95000}};
  assert.equal(analysisContract(c,[r],'LONG_TERM').targets.twelve_months,95000);
  const answer=deterministicStockRadarAnswer({mode:'ACTION_READY',researchContext:c,actionContext:[r]});
  assert.match(answer,/95\.000đ/);assert.match(answer,/70\.000đ/);
  assert.doesNotMatch(appendResearchSnapshot(answer,c,'MWG',false),/MỤC TIÊU DỰ KIẾN VÀ CẮT LỖ/);
});
test('buy email requires a valid stop and the correct horizon target; exits stay available',()=>{
  const card={ticker:'ZZZ',current_state:'BUY',setup:'EARLY_BREAKOUT',position_initial_pct:25,risk_reward:2,horizon:'MEDIUM_TERM',buy_zone:[20000,20500],stop_loss:19000,target:24000,target_near:24000,target_3_6m:28000,target_12m:32000};
  assert.equal(emailPricePlanError({decision_card:card},'EVENT_ALERT'),null);
  assert.match(emailPricePlanError({decision_card:{...card,target_3_6m:null}},'EVENT_ALERT'),/MISSING/);
  assert.match(emailPricePlanError({decision_card:{...card,stop_loss:20100}},'EVENT_ALERT'),/INVALID/);
  assert.equal(emailPricePlanError({decision_card:{current_state:'SELL'}},'EVENT_ALERT'),null);
  for(const html of [actionBody({decision_card:card},'https://stockradar.vn'),dailyBody({opportunities:[{...card,publish_status:'PUBLISHED',action:'MUA'}]},'https://stockradar.vn')])
    for(const value of ['19.000đ','24.000đ','28.000đ','32.000đ','3–6 tháng','12 tháng']) assert.ok(html.includes(value),value);
});
