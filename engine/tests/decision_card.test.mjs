import test from 'node:test';
import assert from 'node:assert/strict';
import {buildDecisionCards,decisionResponse,observationFresh,releasedReport} from '../../supabase/functions/_shared/stockradar-decision.ts';

const now=Date.parse('2026-09-05T06:00:00Z');
const context=()=>({ticker:'FPT',snapshot_id:'research',context_grade:'RESEARCH_READY',as_of_date:'2026-09-04',generated_at:'2026-09-05T02:00:00Z',data_quality:'updated',volume_mode:'EOD',
  quote:{price:100000},technical_detail:{pivot:102000,ma50:99000,ma200:90000,volume:1000,vol20:1200},trade_plan:{stop_loss:90000,buy_zone_low:100000,buy_zone_high:101000}});
const report=()=>({status:'READY',ticker:'FPT',horizon:'SHORT_TERM',snapshot_id:'release',generated_at:'2026-09-05T05:00:00Z',expires_at:'2026-09-05T08:00:00Z',payload:{
  ticker:'FPT',data_grade:'DECISION_GRADE',data_freshness:'FRESH',public_release_allowed:true,current_price:105000,as_of_date:'2026-09-04',volume_mode:'EOD',
  buy_zone_low:104000,buy_zone_high:105000,stop_loss:99000,target_near:117000,target_3_6m:125000,target_12m:135000,risk_reward:2,position_initial_pct:25,
  action_contract:{new_position:{state:'BUY',setup:'EARLY_BREAKOUT',reasons:['Giá vượt nền với khối lượng đạt điều kiện.']},holding:{state:'REDUCE',reasons:['Luận điểm nắm giữ suy yếu.']}}}});

test('research card never promotes preliminary prices to an actionable buy plan',()=>{
  const card=buildDecisionCards([context()],[],'SHORT_TERM','FPT mua được chưa?',now)[0];
  assert.equal(card.conclusion,'CHƯA MUA');assert.equal(card.data.status,'RESEARCH');assert.equal(card.public_action_allowed,false);
  assert.equal(card.stop_loss,null);assert.equal(card.buy_zone.low,null);assert.equal(card.risk_reward,null);
  assert.equal(card.price,100000);assert.equal(card.data.as_of_date,'2026-09-04');
});
test('a sell/hold question without a released holding decision cannot be answered with a new-buy conclusion',()=>{
  for(const question of ['Có nên bán FPT?','FPT nên giữ hay bán?']) {
    const card=buildDecisionCards([context()],[],'SHORT_TERM',question,now)[0];
    assert.equal(card.conclusion,'CHƯA ĐỦ DỮ LIỆU ĐỂ RA QUYẾT ĐỊNH');assert.equal(card.public_action_allowed,false);
  }
  assert.equal(buildDecisionCards([context()],[],'LONG_TERM','Bạn đánh giá FPT một năm thế nào?',now)[0].conclusion,'CHƯA MUA');
});
test('action card preserves canonical lane, price, targets and position without mixing research snapshots',()=>{
  const card=buildDecisionCards([context()],[report()],'SHORT_TERM','FPT mua được chưa?',now)[0];
  assert.equal(card.conclusion,'ĐẠT ĐIỂM MUA – EARLY BREAKOUT');assert.equal(card.price,105000);
  assert.equal(card.moving_averages.ma50,null,'older research snapshot cannot supply technicals to a new release');
  assert.equal(card.position_pct,25);assert.equal(card.targets.twelve_months,135000);assert.equal(card.estimated_plan,null);
  assert.equal(buildDecisionCards([context()],[report()],'SHORT_TERM','Có nên bán FPT?',now)[0].conclusion,'HẠ TỶ TRỌNG');
});
test('an action in one horizon cannot approve a different requested horizon',()=>{
  const card=buildDecisionCards([context()],[report()],'LONG_TERM','FPT 12 tháng',now)[0];
  assert.equal(card.public_action_allowed,false);assert.equal(card.conclusion,'CHƯA MUA');
});
test('stale, future, missing and mock observations fail closed',()=>{
  for(const extra of [{generated_at:null},{generated_at:'2026-09-06T00:00:00Z'},{as_of_date:'2026-09-06'},{data_quality:'stale'},{as_of_date:'2026-08-29'}]) {
    const card=buildDecisionCards([{...context(),...extra}],[],'SHORT_TERM','FPT',now)[0];
    assert.equal(card.data.status,'UNAVAILABLE');assert.match(card.conclusion,/CHƯA ĐỦ DỮ LIỆU/);assert.equal(card.estimated_plan,null);
  }
  for(const extra of [{is_mock:true},{record_mode:'SHADOW'},{data_freshness:'STALE'},{public_release_allowed:false}])assert.equal(releasedReport({...report(),payload:{...report().payload,...extra}},now),false);
  assert.equal(releasedReport({...report(),expires_at:'2026-09-05T04:00:00Z'},now),false);
  assert.equal(observationFresh('2026-09-04','wrong','updated',now),false);
});
test('released report can render when a research cache row is absent',()=>{
  const card=buildDecisionCards([],[report()],'SHORT_TERM','FPT',now)[0];
  assert.equal(card.price,105000);assert.equal(card.public_action_allowed,true);
});
test('an incomplete or oversized buy plan cannot authorize action; an exit lane remains available',()=>{
  for(const extra of [{position_initial_pct:null},{position_initial_pct:100},{stop_loss:106000},{target_near:null},{risk_reward:null}]) {
    const r={...report(),payload:{...report().payload,...extra}};
    assert.equal(releasedReport(r,now),false);
    assert.equal(buildDecisionCards([context()],[r],'SHORT_TERM','FPT mua?',now)[0].public_action_allowed,false);
    assert.equal(releasedReport(r,now,'Có nên bán FPT?'),true);
  }
});
test('server conclusion supersedes contradictory model first line and retains detailed evidence',()=>{
  const response=decisionResponse({scope:'ticker',decision_cards:buildDecisionCards([context()],[],'SHORT_TERM','FPT',now),answer:'KẾT LUẬN: MUA NGAY\n\n4M: Bằng chứng doanh nghiệp.'});
  assert.match(response.answer,/^KẾT LUẬN: FPT — CHƯA MUA/);assert.doesNotMatch(response.answer,/MUA NGAY/);assert.match(response.answer,/4M: Bằng chứng/);
});
