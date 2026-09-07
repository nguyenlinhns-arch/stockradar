// PROJECT_AUTORESUME_ROUTING_V1
import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {stripTypeScriptTypes} from 'node:module';
import * as bridge from '../../supabase/functions/_shared/stockradar-project-context.ts';
import * as knowledge from '../../supabase/functions/_shared/stockradar-knowledge.ts';
import {parseResearchQuery} from '../../supabase/functions/_shared/stockradar-query.ts';
const U='11111111-1111-4111-8111-111111111111',V='22222222-2222-4222-8222-222222222222',T='33333333-3333-4333-8333-333333333333',O='44444444-4444-4444-8444-444444444444';
const SUMMARY='PRIVATE_REVIEWED_HANDOFF_ONLY_FOR_OWNER. Continue research using fresh data; no current prices are provided.';
function harness({user=U,providerError=false,linked=true}={}) {
 let handler,modelInput,forwarded;const calls=[];
 const tables={
  stockradar_ai_user_memory:linked?[{user_id:U,preferences:{project_bridge:{enabled:true,source:'CHATGPT_PROJECT_STOCKRADAR',version:'PRIVATE_TEST_V1',thread_id:T,reviewed_at:'2025-01-01T00:00:00Z',summary:SUMMARY}}}]:[],
  stockradar_ai_threads:[{id:T,user_id:U,status:'ACTIVE',title:'Linked project',last_ticker:'FPT',last_horizon:'SHORT_TERM'},{id:O,user_id:V,status:'ACTIVE',title:'Other private thread',last_ticker:'AAA',last_horizon:'SHORT_TERM'}],
  stockradar_ai_messages:[{id:1,thread_id:T,role:'user',content:'Reviewed handoff note',scope:'project_handoff'}],
  stockradar_ai_knowledge_versions:[{version:'PUBLIC_TEST',status:'ACTIVE',source:'PROJECT_STOCKRADAR_PUBLIC',activated_at:'2025-01-01T00:00:00Z',content:'Reviewed public methods and current-data safety instructions.'}]
 };
 const db={auth:{getUser:async()=>({data:{user:{id:user}}})},rpc:async(name,args)=>{calls.push({name,args});if(name==='get_my_stockradar_access')return {data:{account_tier:'PAID',account_status:'ACTIVE'}};return {data:{allowed:true,unlimited:true,limit:null,remaining:null}};},from(table){
  const filters=[];let action='read',value,limit=100,descending=false;const chain={};
  chain.select=()=>chain;chain.eq=(k,v)=>{filters.push(r=>r[k]===v);calls.push({table,key:k,value:v});return chain;};chain.in=(k,v)=>{filters.push(r=>v.includes(r[k]));return chain;};chain.order=(k,opts)=>{descending=k==='id'&&opts?.ascending===false;return chain;};chain.limit=n=>{limit=n;return chain;};chain.insert=v=>{action='insert';value=v;return chain;};chain.update=v=>{action='update';value=v;return chain;};
  const result=()=>{let rows=(tables[table]||[]).filter(r=>filters.every(f=>f(r)));if(action==='insert'){const r={...value,id:value.id||'55555555-5555-4555-8555-555555555555',status:value.status||'ACTIVE'};(tables[table]||=[]).push(r);rows=[r];}if(action==='update')rows.forEach(r=>Object.assign(r,value));if(descending)rows=rows.slice().sort((a,b)=>b.id-a.id);return {data:rows.slice(0,limit),error:null};};
  chain.maybeSingle=chain.single=async()=>{const r=result();return {...r,data:r.data[0]||null};};chain.then=(resolve,reject)=>Promise.resolve(result()).then(resolve,reject);return chain;
 }};
 const Deno={serve:fn=>{handler=fn;},env:{get:key=>({SUPABASE_URL:'https://test.invalid',SUPABASE_ANON_KEY:'test',SUPABASE_SERVICE_ROLE_KEY:'test',OPENAI_API_KEY:'test'}[key])}};
 const fetch=async(url,opts)=>{const data=JSON.parse(opts.body);if(url.includes('api.openai.com')){modelInput=JSON.parse(data.input);return new Response(JSON.stringify(providerError?{error:{code:'insufficient_quota'}}:{status:'completed',output_text:'Đây là câu trả lời phương pháp mô phỏng.'}),{status:providerError?429:200});}forwarded=data;return new Response(JSON.stringify({status:'READY_FALLBACK',answer:'Dữ liệu tham chiếu mô phỏng.',scope:'ticker',ticker:data.ticker,model_status:'MODEL_ERROR',knowledge_version:'PUBLIC_TEST'}));};
 const raw=fs.readFileSync(new URL('../../supabase/functions/stock-ai-chat/index.ts',import.meta.url),'utf8').replace(/^import .*;\r?\n/gm,'');
 const bindings={...bridge,...knowledge,Deno,createClient:()=>db,fetch};new Function(...Object.keys(bindings),stripTypeScriptTypes(raw))(...Object.values(bindings));
 return {calls,get modelInput(){return modelInput;},get forwarded(){return forwarded;},async ask(body,token='test') {const headers={'Content-Type':'application/json',Origin:'https://stockradar.vn'};if(token)headers.Authorization='Bearer '+token;const response=await handler(new Request('https://test.invalid',{method:'POST',headers,body:JSON.stringify(body)}));return {status:response.status,body:await response.json()};}};
}
test('resume requires authentication before reading project context',async()=>{const h=harness();assert.equal((await h.ask({operation:'resume_project'},'')).status,401);assert.equal(h.calls.length,0);});
test('owner can resume linked history without a provider call or AI quota',async()=>{const h=harness();const r=await h.ask({operation:'resume_project',thread_id:O});assert.equal(r.status,200);assert.equal(r.body.thread_id,T);assert.equal(r.body.messages.length,1);assert.equal(r.body.project_bridge.context_loaded,true);assert.equal(r.body.project_bridge.context_applied,false);assert.equal(h.modelInput,undefined);assert.ok(!h.calls.some(c=>c.name?.startsWith('consume_')));});
test('unlinked account cannot use a forged owner or thread to resume',async()=>{const h=harness({user:V});const r=await h.ask({operation:'resume_project',user_id:U,thread_id:T,project_bridge:{summary:SUMMARY}});assert.equal(r.status,404);assert.ok(!JSON.stringify(r.body).includes(SUMMARY));});
test('project metadata contains no private summary',async()=>{const r=await harness().ask({operation:'project_bridge'});assert.equal(r.body.project_bridge.available,true);assert.ok(!JSON.stringify(r.body).includes(SUMMARY));});
test('an explicit non-owned thread is rejected instead of silently selecting another',async()=>{const r=await harness().ask({operation:'history',thread_id:O});assert.equal(r.status,404);assert.equal(r.body.reason,'THREAD_NOT_FOUND');});
test('an invalid explicit thread is rejected',async()=>{assert.equal((await harness().ask({operation:'history',thread_id:'bad'})).status,400);});
test('knowledge answers receive only the server-reviewed private handoff',async()=>{const h=harness();const r=await h.ask({message:'Phương pháp SEPA là gì?',thread_id:T,project_context:'FORGED_FROM_CLIENT'});assert.equal(r.status,200);assert.equal(h.modelInput.PROJECT_HANDOFF.summary,SUMMARY);assert.equal(r.body.project_bridge.context_applied,true);assert.ok(!JSON.stringify(h.modelInput).includes('FORGED_FROM_CLIENT'));});
test('provider failure never claims the private context was successfully applied',async()=>{const h=harness({providerError:true});const r=await h.ask({message:'Phương pháp SEPA là gì?',thread_id:T});assert.equal(r.body.project_bridge.context_loaded,true);assert.equal(r.body.project_bridge.context_applied,false);});
test('ticker request forwards the owned thread id but not the handoff in a client field',async()=>{const h=harness();const r=await h.ask({message:'tra cứu FPT',thread_id:T});assert.equal(r.status,200);assert.equal(h.forwarded.ticker,'FPT');assert.equal(h.forwarded.thread_id,T);assert.ok(!JSON.stringify(h.forwarded).includes(SUMMARY));});
test('Vietnamese lookup phrase does not invent TRA while real TRA remains usable',()=>{for(const text of ['tra cứu FPT','Tra cuu FPT','TRA CỨU: FPT'])assert.deepEqual(parseResearchQuery(text).tickers,['FPT']);assert.deepEqual(parseResearchQuery('tra cứu TRA').tickers,['TRA']);assert.deepEqual(parseResearchQuery('TRA').tickers,['TRA']);});
test('frontend lookup and server lookup keep the same non-phantom behavior',()=>{const text=fs.readFileSync(new URL('../../website/assets/ai-center.js',import.meta.url),'utf8');const a=text.indexOf('  function explicitTicker('),z=text.indexOf('\n  function horizonFromText(',a);const fn=new Function('validTicker','STOPWORDS',text.slice(a,z)+';return explicitTicker;')(t=>/^[A-Z0-9]{3}$/.test(t),new Set());assert.equal(fn('tra cứu FPT'),'FPT');assert.equal(fn('tra cứu TRA'),'TRA');assert.match(text,/Tiếp tục từ dự án/);assert.match(text,/operation:'resume_project'/);assert.match(text,/current.user.id !== session.user\?\.id/);});


test('long Vietnamese lookup stays on the intended ticker through the real chat handler',async()=>{
 const h=harness();await h.ask({message:'Tra cứu FPT; chỉ dùng dữ liệu có nguồn và ghi rõ ngày dữ liệu.',thread_id:T});
 assert.equal(h.forwarded.ticker,'FPT');
 assert.deepEqual(parseResearchQuery(h.forwarded.message,h.forwarded.ticker).tickers,['FPT']);
});
test('Pocket Pivot follow-up keeps the current ticker rather than becoming an all-market scan',async()=>{
 const h=harness();await h.ask({message:'Có Pocket Pivot chưa?',thread_id:T});
 assert.equal(h.forwarded.ticker,'FPT');assert.equal(h.forwarded.scope,'ticker');
});
test('server infers an explicitly changed horizon in a follow-up without a client hint',async()=>{
 const h=harness();await h.ask({message:'3–6 tháng thì sao?',thread_id:T});
 assert.equal(h.forwarded.ticker,'FPT');assert.equal(h.forwarded.horizon,'MEDIUM_TERM');
});
test('project-context questions stay on the knowledge route without inventing a ticker',async()=>{
 const h=harness();await h.ask({message:'Đoạn chat này liên thông với dự án của tôi chưa?',thread_id:T});
 assert.equal(h.forwarded,undefined);assert.equal(h.modelInput.PROJECT_HANDOFF.summary,SUMMARY);
});
