import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import * as core from '../../supabase/functions/_shared/stockradar-core.ts';
import * as view from '../../supabase/functions/_shared/stockradar-research-view.ts';
import * as query from '../../supabase/functions/_shared/stockradar-query.ts';
import * as decision from '../../supabase/functions/_shared/stockradar-decision.ts';
import * as modelStatus from '../../supabase/functions/_shared/model-status.ts';
import * as projectKnowledge from '../../supabase/functions/_shared/stockradar-knowledge.ts';

const reviewedKnowledge = Object.freeze({
  version:'FIXTURE_PROJECT_V2',title:'Reviewed public test methods',status:'ACTIVE',
  source:'PROJECT_STOCKRADAR_PUBLIC',activated_at:'2025-01-01T00:00:00Z',
  content:'FIXTURE_REVIEWED_PUBLIC_METHOD_SEQUENCE: use 4M, CANSLIM, SEPA and VPA; never bypass current-data gates.'
});

function harness({guest=false,tier='FREE',quota=true,burst=true,stale=false,incomplete=false,watch=[],knowledge=reviewedKnowledge,knowledgeError=false}={}) {
  let handler, modelInput, modelRequest, quotaCalls=0;
  const calls=[];
  const context=ticker=>({status:'INTERNAL_RESEARCH_READY',context_grade:'RESEARCH_READY',ticker,
    snapshot_id:'fixture-observation',generated_at:stale?'2020-01-01T00:00:00Z':new Date().toISOString(),as_of_date:new Date(Date.now()+7*3600000).toISOString().slice(0,10),data_quality:'updated',
    payload:{quote:{price:12345},setup:{new_position_state_v5:'WATCH'},technical_detail:{ma20:12000,volume:500000}}});
  const db={auth:{getUser:async()=>({data:{user:{id:'user-a'}}})},
    rpc:async(name,args)=>{
      calls.push({name,args});
      if(name==='get_my_stockradar_access')return {data:{account_tier:tier,account_status:'ACTIVE'}};
      if(name==='fetch_stockradar_ai_context')return {data:context(args.p_ticker)};
      if(name==='query_stockradar_research')return {data:{items:[context('HPG'),context('NKG')]}};
      if(name==='fetch_stockradar_cached_report')return {data:{status:'BLOCKED'}};
      if(args?.p_bucket==='stock_ai_burst')return {data:{allowed:burst,retry_after:60}};
      if(name.includes('consume_')){quotaCalls++;return {data:{allowed:quota,limit:tier==='PAID'?null:guest?3:10,remaining:tier==='PAID'?null:0,unlimited:tier==='PAID'}};}
      return {data:null};
    },
    from:table=>{
      calls.push({name:'from',args:[table]});
      const chain={};for(const k of ['select','eq','is','in','order','limit'])chain[k]=(...args)=>{calls.push({name:k,args,table});return chain;};
      chain.maybeSingle=async()=>{
        assert.equal(table,'stockradar_ai_knowledge_versions');
        return knowledgeError?{data:null,error:{code:'FIXTURE_READ_FAILED'}}:{data:knowledge,error:null};
      };
      chain.then=resolve=>Promise.resolve({data:table==='watchlist_items'?watch:[]}).then(resolve);return chain;
    }};
  const Deno={serve:fn=>{handler=fn;},env:{get:name=>({SUPABASE_URL:'https://fixture.invalid',SUPABASE_ANON_KEY:'anon',SUPABASE_SERVICE_ROLE_KEY:'test-only',OPENAI_API_KEY:'test-only'}[name])}};
  const fetchMock=async(url,args)=>{modelRequest=JSON.parse(args.body);modelInput=JSON.parse(modelRequest.input);return new Response(JSON.stringify({status:incomplete?'incomplete':'completed',output_text:'KẾT LUẬN: THEO DÕI. DỮ LIỆU: 04/09/2026.'}));};
  const bindings={...core,...view,...query,...decision,...modelStatus,...projectKnowledge,Deno,createClient:()=>db,fetch:fetchMock};
  const source=fs.readFileSync(new URL(`../../supabase/functions/${guest?'stock-ai-guest':'stock-ai'}/index.ts`,import.meta.url),'utf8').replace(/^import .*;\r?\n/gm,'');
  new Function(...Object.keys(bindings),source.replace("} catch { return json({status:'SERVICE_UNAVAILABLE',answer:","} catch (error) { throw error; return json({status:'SERVICE_UNAVAILABLE',answer:"))(...Object.values(bindings));
  return {calls,get modelInput(){return modelInput},get modelRequest(){return modelRequest},get quotaCalls(){return quotaCalls},async ask(message,extra={}){
    const r=await handler(new Request('https://fixture.invalid',{method:'POST',headers:{authorization:'Bearer test-only','cf-connecting-ip':'203.0.113.1'},body:JSON.stringify({message,guest_id:'test-only-guest-identity',...extra})}));
    return {status:r.status,body:await r.json()};
  }};
}

test('authenticated inferred ticker uses the same ticker for data, report and output',async()=>{
  const h=harness();const r=await h.ask('Phân tích HPG');
  assert.equal(r.status,200);assert.equal(r.body.ticker,'HPG');
  assert.equal(r.body.analysis[0].technical.ma20,12000);
  assert.equal(h.calls.filter(x=>x.name==='fetch_stockradar_ai_context').length,1);
  assert.ok(h.calls.filter(x=>x.name==='fetch_stockradar_cached_report').every(x=>x.args.p_ticker==='HPG'));
});
test('guest scan and comparison use real data routes without private portfolio',async()=>{
  for(const question of ['Top cổ phiếu ngân hàng','Quét Pocket Pivot','Cổ phiếu nào đang gần breakout?','So sánh HPG và NKG']){
    const h=harness({guest:true});const r=await h.ask(question);
    assert.equal(r.status,200);assert.equal(r.body.analysis.length,2);
    assert.equal(h.modelInput.USER_CONTEXT.portfolio_available,false);
    // Guests may read approved public methodology server-side, but never a user's positions.
    assert.equal(h.calls.some(x=>x.name==='from'&&x.args[0]==='watchlist_items'),false);
    assert.ok(h.calls.filter(x=>x.name==='from').every(x=>x.args[0]==='stockradar_ai_knowledge_versions'));
  }
});
test('quota denial never calls provider and paid null remains unlimited',async()=>{
  for(const guest of [false,true]){
    const h=harness({guest,quota:false});const r=await h.ask('HPG mua được chưa?');
    assert.equal(r.status,429);assert.equal(h.modelInput,undefined);assert.equal(h.quotaCalls,1);
    assert.equal(h.calls.some(x=>x.name==='from'&&x.args[0]==='stockradar_ai_knowledge_versions'),false);
  }
  const h=harness({tier:'PAID'});const r=await h.ask('HPG mua được chưa?');
  assert.equal(r.body.quota.unlimited,true);assert.equal(r.body.quota.limit,null);assert.equal(r.body.quota.remaining,null);
});
test('single ticker never forwards unrelated positions; portfolio is owner scoped',async()=>{
  const watch=[{ticker:'HPG',owns_stock:true,horizon:'SHORT_TERM',cost_basis:12300},{ticker:'NKG',owns_stock:true,horizon:'SHORT_TERM',cost_basis:25000}];
  const h=harness({watch});await h.ask('Phân tích HPG');
  assert.deepEqual(h.modelInput.USER_CONTEXT.watchlist.map(x=>x.ticker),['HPG']);
  assert.ok(h.calls.some(x=>x.name==='eq'&&x.args[0]==='user_id'&&x.args[1]==='user-a'));
  const all=harness({watch});const r=await all.ask('Danh mục của tôi',{scope:'portfolio'});
  assert.equal(r.status,200);assert.equal(r.body.analysis.length,2);
});
test('incomplete provider response uses accurately labelled deterministic fallback',async()=>{
  const h=harness({incomplete:true});const r=await h.ask('Phân tích HPG');
  assert.equal(r.body.answer_engine,'STOCKRADAR_CORE');assert.equal(r.body.status,'READY_FALLBACK');
  assert.equal(r.body.knowledge_status,'ACTIVE');assert.equal(r.body.knowledge_applied,false);
});

test('guest and signed-in answers append full research only on a detailed request',async()=>{
  for(const guest of [false,true]) for(const incomplete of [false,true]){
    const h=harness({guest,incomplete});
    const simple=await h.ask('Phân tích HPG');
    assert.doesNotMatch(simple.body.answer,/DỮ LIỆU NGHIÊN CỨU STOCKRADAR/);
    assert.ok(simple.body.research_data);
    const detailed=await h.ask('Phân tích chi tiết HPG');
    assert.match(detailed.body.answer,/DỮ LIỆU NGHIÊN CỨU STOCKRADAR/);
  }
});

test('paid technical burst denial preserves daily unlimited entitlement and never calls inference',async()=>{
 const h=harness({tier:'PAID',burst:false});const r=await h.ask('Phân tích HPG');
 assert.equal(r.status,429);assert.equal(r.body.reason,'TECHNICAL_RATE_LIMIT');assert.equal(r.body.quota_consumed,false);assert.equal(h.quotaCalls,0);assert.equal(h.modelInput,undefined);
 assert.ok(!h.calls.some(x=>x.name==='fetch_stockradar_ai_context'));
 assert.equal(h.calls.some(x=>x.name==='from'&&x.args[0]==='stockradar_ai_knowledge_versions'),false);
});

test('stale observations cannot reach a provider or a scenario price even if a cache labels them research ready',async()=>{
 for(const guest of [false,true]){const h=harness({guest,stale:true});const r=await h.ask('FPT mua được chưa?');
 assert.equal(r.body.mode,'METHOD_ONLY');assert.equal(h.modelInput,undefined);assert.equal(r.body.decision_cards[0].public_action_allowed,false);assert.equal(r.body.decision_cards[0].price,null);assert.match(r.body.answer,/CHƯA ĐỦ DỮ LIỆU/);assert.equal(r.body.knowledge_applied,false);}
});

test('both research handlers apply the real reviewed loader and report the version honestly',async()=>{
 for(const guest of [false,true]){
  const h=harness({guest});const r=await h.ask('Phân tích HPG');
  assert.equal(r.status,200);assert.ok(h.modelRequest.instructions.startsWith(core.STOCKRADAR_SYSTEM_CORE));
  assert.ok(h.modelRequest.instructions.includes(reviewedKnowledge.content));
  assert.equal(h.modelRequest.store,false);
  assert.equal(r.body.knowledge_version,reviewedKnowledge.version);assert.equal(r.body.knowledge_status,'ACTIVE');
  assert.equal(r.body.knowledge_sync_mode,'REVIEWED_PROJECT_SNAPSHOT');assert.equal(r.body.knowledge_applied,true);
  assert.ok(!JSON.stringify(r.body).includes(reviewedKnowledge.content));
  assert.ok(h.calls.some(x=>x.table==='stockradar_ai_knowledge_versions'&&x.name==='eq'&&x.args[0]==='status'&&x.args[1]==='ACTIVE'));
  assert.ok(h.calls.some(x=>x.table==='stockradar_ai_knowledge_versions'&&x.name==='in'&&x.args[0]==='source'));
 }
});
test('knowledge read failures retain static safety instructions without claiming knowledge application',async()=>{
 for(const guest of [false,true]){
  const h=harness({guest,knowledgeError:true});const r=await h.ask('Phân tích HPG');
  assert.equal(r.status,200);assert.equal(h.modelRequest.instructions,core.STOCKRADAR_SYSTEM_CORE);
  assert.equal(r.body.knowledge_version,'STATIC_CORE');assert.equal(r.body.knowledge_status,'STATIC_FALLBACK');
  assert.equal(r.body.knowledge_applied,false);assert.equal(r.body.knowledge_reason,'KNOWLEDGE_READ_FAILED');
 }
});
test('client-supplied knowledge cannot replace server-reviewed methodology',async()=>{
 for(const guest of [false,true]){
  const h=harness({guest});const r=await h.ask('Phân tích HPG',{knowledge:'CLIENT_OVERRIDE_UNREVIEWED',knowledge_version:'CLIENT_VERSION'});
  assert.ok(h.modelRequest.instructions.includes(reviewedKnowledge.content));
  assert.ok(!h.modelRequest.instructions.includes('CLIENT_OVERRIDE_UNREVIEWED'));
  assert.equal(r.body.knowledge_version,reviewedKnowledge.version);
 }
});
