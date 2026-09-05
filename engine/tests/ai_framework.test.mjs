import test from 'node:test';
import assert from 'node:assert/strict';
import {normalizeResearchContext,deterministicStockRadarAnswer,hasResearchFramework} from '../../supabase/functions/_shared/stockradar-core.ts';
import {analysisContract} from '../../supabase/functions/_shared/stockradar-research-view.ts';
import {fourHorizonEvidence} from '../../supabase/functions/_shared/stockradar-framework.ts';
const raw={status:'INTERNAL_RESEARCH_READY',ticker:'ZZZ',as_of_date:'2026-09-04',payload:{volume_mode:'EOD',business_bucket:'BANK',quote:{price:22200},technical_detail:{ma20:22300,ma50:22500,ma200:21222,pivot20:22800,volume:7950500,vol20:8898740,stage:'STAGE_1_TO_2',computed_indicators:{stage:'STAGE_1',trend_template_pass:false,vcp_proxy:false,max_down_volume10:10284000}},fundamental_detail:{period_end:'202606',roe_pct:19.92,roa_pct:1.91,pbt_growth_yoy_pct:11.1,pbt_growth_3y_avg_pct:4.98,eps_ttm:3730.45,bvps:17796.69,pe_median_8q_provider:7.04,pb_median_8q_provider:1.325},valuation_detail:{pe:5.951,pb:1.2474,base:25323,bull:29122,fair_value:25323,assumptions_verified:false},trade_plan:{target_3_6m:24117,target_12m:29122},research_v7:{target_3_6m_v5:24117,target_12m_v5:29122}}};
test('unverified historical valuations cannot leak as time-specific targets through any response channel',()=>{
  const c=normalizeResearchContext(raw),a=analysisContract(c);
  assert.equal(c.trade_plan.target_3_6m,null);assert.equal(c.analysis.target_12m_v5,null);assert.equal(c.research_v7.target_3_6m_v5,null);
  assert.equal(a.targets.three_to_six_months,null);assert.equal(a.targets.twelve_months,null);assert.equal(a.valuation.fair_value,null);
  const answer=deterministicStockRadarAnswer({mode:'RESEARCH_ONLY',researchContext:c,question:'ZZZ trong 3–6 tháng'});
  assert.doesNotMatch(answer,/24\.117|29\.122|25\.323/);
  assert.ok(hasResearchFramework(answer));
  for(const v of ['19,9%','11,1%','22.500đ','10.284.000','5,95','1,25'])assert.ok(answer.includes(v),v);
  assert.match(answer,/trước thuế tăng 11,1%/);assert.doesNotMatch(answer,/sau thuế tăng 11,1%/);
  assert.equal(raw.payload.trade_plan.target_3_6m,24117,'source object must not be mutated');
});
test('short horizon contains technical evidence and does not inherit medium/long forecasts',()=>{
  const h=fourHorizonEvidence(normalizeResearchContext(raw));
  assert.deepEqual(h.map(x=>x.horizon),['SHORT_TERM','MEDIUM_TERM','LONG_TERM','ACCUMULATION']);
  for(const v of ['22.300đ','22.500đ','22.800đ','7.950.500','10.284.000','tạo nền'])assert.ok(h[0].text.includes(v),v);
  assert.match(h[1].text,/11,1%/);assert.match(h[2].text,/19,9%/);assert.match(h[3].text,/không dùng biến động vài phiên/);
});
test('a model answer that drops the four layers or horizons fails the response contract',()=>{
  assert.equal(hasResearchFramework('KẾT LUẬN: ZZZ tham khảo 24.117đ, tăng 8,6%.'),false);
  assert.equal(hasResearchFramework('4M CANSLIM SEPA VPA Ngắn hạn 3–6 tháng 12 tháng'),false);
});
