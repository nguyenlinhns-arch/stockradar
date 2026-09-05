import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

function harness({firstDay=null,search=''}={}) {
  const events=[],local=new Map(),session=new Map();
  if(firstDay!==null)local.set('sr_meaningful_activation_day_v1',String(firstDay));
  const storage=m=>({getItem:k=>m.has(k)?m.get(k):null,setItem:(k,v)=>m.set(k,String(v))});
  const window={location:{pathname:'/',search},StockRadarDecisionView:{stillFresh:d=>d.fresh===true}};
  vm.runInNewContext(fs.readFileSync(new URL('../../website/assets/conversion-v3.js',import.meta.url),'utf8'),{
    window,document:{body:{dataset:{}},referrer:'',querySelector:()=>null,querySelectorAll:()=>[]},URL,URLSearchParams,Date,
    localStorage:storage(local),sessionStorage:storage(session),crypto:{randomUUID:()=> 'test-only-browser-session'},
    fetch:async(url,options)=>{events.push(JSON.parse(options.body));return{};}
  });
  return {events,analytics:window.StockRadarAnalytics,local};
}
const answer=()=>({tier:'FREE',scope:'ticker',message:'private question',holdings:{ZZZ:123},decision_cards:[{ticker:'ZZZ',data:{fresh:true,status:'RESEARCH',source_status:'RESEARCH_READY'}}]});
test('activation requires a useful fresh single-ticker report and never sends conversation or portfolio',()=>{
  const h=harness();assert.deepEqual(h.events.map(e=>e.event_name),['home_view']);
  const stale=answer();stale.decision_cards[0].data.fresh=false;h.analytics.aiResult(stale);
  assert.equal(h.events.length,1);
  h.analytics.aiSubmitted();h.analytics.aiResult(answer());h.analytics.aiResult(answer());
  for(const action of ['ai_interaction','meaningful_report','free_activation'])assert.equal(h.events.filter(e=>e.action_name===action).length,1);
  assert.ok(h.local.has('sr_meaningful_activation_day_v1'));
  for(const event of h.events)for(const key of ['message','holdings','answer','portfolio','token','email'])assert.equal(key in event,false);
});
test('D1/D7 browser returns require another meaningful analysis; email attribution carries no recipient identifier',()=>{
  const today=Math.floor((Date.now()+7*3600000)/86400000);
  for(const days of [1,7]) {
    const h=harness({firstDay:today-days,search:'?utm_source=stockradar_email&utm_campaign=action_alert'});
    assert.equal(h.events.filter(e=>e.action_name?.startsWith('meaningful_return')).length,0);
    assert.equal(h.events.filter(e=>e.action_name==='email_cta_landing').length,1);
    h.analytics.aiResult(answer());h.analytics.aiResult(answer());
    assert.equal(h.events.filter(e=>e.action_name===`meaningful_return_d${days}`).length,1);
    assert.equal(h.events.filter(e=>e.action_name==='free_activation').length,0);
  }
});
