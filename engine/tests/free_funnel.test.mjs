import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {randomUUID} from 'node:crypto';
import {stripTypeScriptTypes} from 'node:module';
import * as funnel from '../../supabase/functions/_shared/funnel.ts';
import {modelStatus} from '../../supabase/functions/_shared/model-status.ts';

const source=fs.readFileSync(new URL('../../website/assets/conversion-v3.js',import.meta.url),'utf8');
const storage=m=>({getItem:k=>m.get(k)||null,setItem:(k,v)=>m.set(k,String(v))});
function browser({url='https://stockradar.vn/',referrer='',local=new Map(),session=new Map(),pixel=true,optOut=false}={}) {
 const network=[],scripts=[],location=new URL(url);
 const window={location,STOCKRADAR_META_CONFIG:{enabled:pixel,pixelId:'123456789012345'}};
 const document={body:{dataset:{}},referrer,documentElement:{classList:{add(){}}},querySelector:()=>null,querySelectorAll:()=>[],head:{append:s=>scripts.push(s)},createElement:()=>({})};
 vm.runInNewContext(source,{window,document,URL,URLSearchParams,Date,crypto:{randomUUID},navigator:{globalPrivacyControl:optOut},localStorage:storage(local),sessionStorage:storage(session),fetch:async(u,o)=>{network.push(JSON.parse(o.body));return{};}});
 return {api:window.StockRadarAnalytics,window,local,session,scripts,network,meta:()=>Array.from(window.fbq?.queue||[],a=>Array.from(a))};
}
const receipt={registration_created:true,event_id:'12345678-1111-4111-8111-123456789012',plan:'free'};
test('first/last touch and fbclid survive route/reload without transmitting click IDs or PII',()=>{
 const h=browser({url:'https://stockradar.vn/?utm_source=facebook&utm_campaign=free_launch&fbclid=Abcde_123456789'});
 const s=browser({url:'https://stockradar.vn/signup/?plan=free',local:h.local,session:h.session,referrer:'https://stockradar.vn/'});
 assert.equal(s.api.attribution().first.utm_campaign,'free_launch');assert.equal(s.api.attribution().last.source,'facebook');assert.equal(s.api.attribution().first.fbclid,'Abcde_123456789');
 s.api.aiSubmitted({tier:'FREE',ticker:'FPT',message:'secret@email.invalid',holdings:{FPT:123},horizon:'LONG_TERM'});
 s.api.signupAccepted(receipt);
 const payload=JSON.stringify([...s.network,...s.meta()]);assert.doesNotMatch(payload,/secret@|holdings|Abcde_123456789/);
 assert.deepEqual(Object.keys(s.meta().find(e=>e[1]==='AIQuestion')[2]).sort(),['horizon','source_page','ticker','tier']);
 const other=browser({url:'https://stockradar.vn/?utm_source=instagram&utm_campaign=return',local:h.local,session:h.session});
 assert.equal(other.api.attribution().first.source,'facebook');assert.equal(other.api.attribution().last.source,'instagram');
});
test('completion needs actual server receipt, is stable once across reload, and never re-inserts browser completion',()=>{
 const h=browser({url:'https://stockradar.vn/signup/?plan=free'});
 h.api.signupStarted();h.api.signupStarted();h.api.signupSubmitted();
 h.api.track('signup_complete');h.api.signupAccepted({registration_created:false});h.api.signupAccepted({registration_created:true,event_id:'invalid'});
 assert.equal(h.meta().filter(e=>e[1]==='CompleteRegistration').length,0);
 h.api.signupAccepted(receipt);h.api.signupAccepted(receipt);
 assert.equal(h.meta().filter(e=>e[1]==='StartRegistration').length,1);
 const event=h.meta().filter(e=>e[1]==='CompleteRegistration');assert.equal(event.length,1);assert.equal(event[0][3].eventID,receipt.event_id);
 assert.equal(h.network.some(e=>e.event_name==='signup_completed'),false);
 const reload=browser({url:'https://stockradar.vn/signup/?plan=free',local:h.local,session:h.session});reload.api.signupAccepted(receipt);reload.api.signupStarted();
 assert.equal(reload.meta().filter(e=>['CompleteRegistration','StartRegistration'].includes(e[1])).length,0);
});
test('CTA impressions persist and signed-in accounts cannot see a Guest CTA',()=>{
 const h=browser();assert.equal(h.api.guestCta('first','GUEST'),true);assert.equal(h.api.guestCta('first','GUEST'),false);
 const reload=browser({local:h.local,session:h.session});assert.equal(reload.api.guestCta('first','GUEST'),false);
 assert.equal(reload.api.guestCta('last','GUEST'),true);assert.equal(reload.api.guestCta('last','GUEST'),false);
 for(const tier of ['FREE','PREMIUM','PAID'])for(const kind of ['first','last','exhausted'])assert.equal(reload.api.guestCta(kind,tier),false);
});
test('legacy aliases share canonical impression and form-flow dedupe',()=>{
 const h=browser();h.api.track('pro_view');h.api.track('pro_page_view');h.api.track('premium_view');
 assert.equal(h.network.filter(e=>e.event_name==='premium_view').length,1);
 h.api.track('signup_start');h.api.signupStarted();assert.equal(h.network.filter(e=>e.event_name==='signup_started').length,1);
});
test('fallback, method-only, timeout and credit blockage are not model success',()=>{
 const h=browser();
 for(const d of [{status:'READY',mode:'METHOD_ONLY',answer_engine:'STOCKRADAR_CORE'},{status:'READY_FALLBACK',reason:'OPENAI_429_CREDIT_BALANCE_EXHAUSTED',answer_engine:'STOCKRADAR_CORE'},{status:'READY_FALLBACK',reason:'OPENAI_TIMEOUT',answer_engine:'STOCKRADAR_CORE'}])assert.equal(h.api.aiResult({...d,answer:'Reference'}),false);
 assert.equal(h.network.filter(e=>e.event_name==='ai_result_success').length,0);
 assert.equal(modelStatus({reason:'OPENAI_TIMEOUT'}),'MODEL_TIMEOUT');assert.equal(modelStatus({reason:'OPENAI_429_CREDIT_BALANCE_EXHAUSTED'}),'MODEL_CREDIT_BLOCKED');
 assert.equal(h.api.aiResult({status:'READY',answer_engine:'MODEL_STOCKRADAR',answer:'Actual provider fixture'}),true);
});
test('SDK is async and optional; opt out, sensitive URLs/referrers and blocked script fail quietly',()=>{
 for(const options of [{pixel:false},{optOut:true},{url:'https://stockradar.vn/#access_token=private'},{url:'https://stockradar.vn/?utm_campaign=email%40private.invalid'},{url:'https://stockradar.vn/?next=%2F%3Ftoken%3Dprivate'},{referrer:'https://stockradar.vn/?utm_term=email%40private.invalid'}]){
  const h=browser(options);assert.equal(h.scripts.length,0);h.api.aiSubmitted();assert.ok(h.network.length>=1);
 }
 const h=browser();assert.equal(h.scripts.length,1);assert.equal(h.scripts[0].async,true);h.scripts[0].onerror();h.api.aiSubmitted();assert.equal(h.api.meta.status,'PIXEL_SCRIPT_BLOCKED');
});
function endpoint({name='signup-link',created=false,authError=false,measurementError=false}={}) {
 let handle;const requests=[],signups=[];
 const Deno={serve:f=>handle=f,env:{get:k=>({SUPABASE_URL:'https://fixture.invalid',SUPABASE_ANON_KEY:'public-fixture',SUPABASE_SERVICE_ROLE_KEY:'server-fixture'}[k])}};
 const fetch=async(url,options)=>{requests.push({url,body:options?.body?JSON.parse(options.body):null});
  if(url.endsWith('/settings'))return Response.json({mailer_autoconfirm:false});
  return Response.json(url.includes('finalize_')?{...receipt,registration_created:created}:true,{status:measurementError?503:200});};
 const createClient=()=>({auth:{signUp:async b=>{signups.push(b);return {data:{user:{id:randomUUID()},session:null},error:authError?{status:409}:null};}}});
 const bindings={...funnel,Deno,fetch,createClient};
 const code=fs.readFileSync(new URL(`../../supabase/functions/${name}/index.ts`,import.meta.url),'utf8').replace(/^import .*;\r?\n/gm,'');
 new Function(...Object.keys(bindings),stripTypeScriptTypes(code))(...Object.values(bindings));
 return {requests,signups,run:(body,ua='Mozilla/5.0')=>handle(new Request('https://fixture.invalid',{method:'POST',headers:{origin:'https://stockradar.vn','content-type':'application/json','user-agent':ua},body:JSON.stringify(body)}))};
}
const submission=()=>({email:'qa@example.invalid',password:'Test-only-123!',terms_accepted:true,privacy_accepted:true,measurement:{flow_id:randomUUID(),session_id:randomUUID(),first_touch:{source:'facebook',utm_campaign:'free_launch',email:'private'}}});
test('signup conversion reflects server receipt, never generic Auth acceptance or a failed measurement request',async()=>{
 for(const options of [{created:true},{created:false},{created:true,authError:true},{created:true,measurementError:true}]){
  const h=endpoint(options),r=await h.run(submission()),body=await r.json();
  assert.equal(body.registration_created===true,options.created&&!options.authError&&!options.measurementError);
  if(!options.authError)assert.equal(body.verification_required,true);
  const rpc=h.requests.find(r=>r.url.includes('finalize_'));if(rpc)assert.doesNotMatch(JSON.stringify(rpc.body),/qa@|private|Test-only/);
 }
});
test('bot/honeypot/invalid consent are rejected before Auth, with no completion',async()=>{
 for(const [body,ua] of [[{...submission(),company:'spam'},'Mozilla'],[submission(),'facebookexternalhit/1.1'],[{...submission(),terms_accepted:false},'Mozilla']]){
  const h=endpoint({created:true}),r=await h.run(body,ua);assert.equal(r.status,400);assert.equal(h.signups.length,0);assert.equal(h.requests.length,0);
 }
});
test('measurement drops known bots and rejects forged completion; only a strict envelope reaches storage',async()=>{
 const h=endpoint({name:'conversion-event'}),body={schema_version:'STOCKRADAR_FUNNEL_V2',event_name:'ai_question_started',event_id:randomUUID(),session_id:randomUUID(),source_path:'/',tier:'GUEST',message:'private',email:'private@example.invalid',first_touch:{utm_campaign:'email@example.invalid',source:'facebook'}};
 assert.equal((await h.run(body,'HeadlessChrome')).status,202);assert.equal(h.requests.length,0);
 assert.equal((await h.run({...body,event_name:'signup_completed'})).status,400);assert.equal(h.requests.length,0);
 assert.equal((await h.run(body)).status,202);assert.equal(h.requests.length,1);assert.doesNotMatch(JSON.stringify(h.requests),/private|example.invalid/);
});
