import test from 'node:test';
import assert from 'node:assert/strict';
import {buildResearchSnapshot,analysisContract} from '../../supabase/functions/_shared/stockradar-research-view.ts';
import {parseResearchQuery,guestQuotaIdentity} from '../../supabase/functions/_shared/stockradar-query.ts';
import {normalizeResearchContext,deterministicStockRadarAnswer} from '../../supabase/functions/_shared/stockradar-core.ts';

test('missing research values never turn into zero prices or targets',()=>{
  const r=buildResearchSnapshot({ticker:'HPG',quote:{price:null},valuation_detail:{pe:null},trade_plan:{stop_loss:null}});
  assert.equal(r.price,null);assert.equal(r.valuation.pe,null);assert.equal(r.trade_plan.stop_loss,null);
  assert.equal(r.trade_plan.target_12m_upside_pct,null);
});
test('source zero volume is preserved and alias fallback works',()=>{
  const r=buildResearchSnapshot({ticker:'HPG',technical_detail:{volume:0,pivot20:null,pivot:100}});
  assert.equal(r.setup.volume,0);assert.equal(r.setup.pivot,100);
});
test('EOD volume never selects an intraday projection',()=>{
  const context={ticker:'HPG',context_grade:'RESEARCH_READY',volume_mode:'EOD',technical_detail:{rvol:0.68,rvol_progress_adjusted:1.4},quote:{price:100}};
  assert.equal(buildResearchSnapshot(context).setup.rvol,0.68);
  assert.match(deterministicStockRadarAnswer({mode:'RESEARCH_ONLY',researchContext:context}),/cuối phiên, thấp hơn khoảng 32% so với mức trung bình 20 phiên trước/);
});
test('ticker, comparison, scans and sector intents route separately',()=>{
  assert.deepEqual(parseResearchQuery('So sánh HPG và NKG').tickers,['HPG','NKG']);
  assert.equal(parseResearchQuery('Phân tích HPG').scope,'ticker');
  assert.equal(parseResearchQuery('Top 5 cổ phiếu hiện tại').scope,'scan');
  assert.equal(parseResearchQuery('Quét Pocket Pivot').filter,'pocket_pivot');
  assert.equal(parseResearchQuery('Cổ phiếu nào đang gần breakout?').filter,'near_pivot');
  assert.equal(parseResearchQuery('Top cổ phiếu ngân hàng').sector,'Ngân hàng');
});
test('rotating guest id cannot rotate the database quota identity',async()=>{
  const req=id=>new Request('https://stockradar.test',{method:'POST',headers:{'cf-connecting-ip':'203.0.113.8'},body:JSON.stringify({guest_id:id})});
  assert.equal(await guestQuotaIdentity(req('a'),'test-secret'),await guestQuotaIdentity(req('b'),'test-secret'));
  assert.equal(await guestQuotaIdentity(new Request('https://stockradar.test'),'test-secret'),null);
});
test('stale data has an explicit warning and never a probability claim',()=>{
  const c=normalizeResearchContext({status:'INTERNAL_REFERENCE_READY',ticker:'HPG',data_quality:'stale',payload:{quote:{price:100}}});
  assert.match(deterministicStockRadarAnswer({mode:'REFERENCE_ONLY',researchContext:c}),/dữ liệu cũ/);
  assert.equal(analysisContract(c).probability,null);
  assert.equal(analysisContract(c).public_action_allowed,false);
});
