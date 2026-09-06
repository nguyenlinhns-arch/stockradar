import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {stripTypeScriptTypes} from 'node:module';

function signup({autoConfirm=false,error=null,session=null}={}) {
  let handler;const calls=[];
  const Deno={env:{get:n=>({SUPABASE_URL:'https://fixture.invalid',SUPABASE_ANON_KEY:'public-fixture'}[n])},serve:fn=>handler=fn};
  const fetch=async()=>new Response(JSON.stringify({mailer_autoconfirm:autoConfirm,disable_signup:false}));
  const createClient=(url,key)=>{calls.push({url,key});return {auth:{signUp:async args=>{calls.push(args);return {data:{user:{id:'user'},session},error};}}};};
  const source=fs.readFileSync(new URL('../../supabase/functions/signup-link/index.ts',import.meta.url),'utf8').replace(/^import .*;\r?\n/gm,'');
  new Function('Deno','fetch','createClient',stripTypeScriptTypes(source))(Deno,fetch,createClient);
  return {calls,run:(plan='free')=>handler(new Request('https://fixture.invalid',{method:'POST',headers:{'content-type':'application/json',origin:'https://stockradar.vn'},body:JSON.stringify({email:'qa@example.invalid',password:'Local-test-Only-123!',plan,terms_accepted:true,privacy_accepted:true})}))};
}

test('signup uses public Auth and waits for email ownership; no auto login or Premium grant',async()=>{
  for(const plan of ['free','premium']){
    const h=signup(),r=await h.run(plan),body=await r.json();
    assert.equal(r.status,202);assert.equal(body.verification_required,true);
    assert.equal(h.calls[0].key,'public-fixture');
    assert.equal(h.calls[1].email_confirm,undefined);
    assert.equal(h.calls[1].options.data.account_tier,undefined);
    assert.equal(h.calls[1].options.data.selected_plan_interest,plan);
    assert.equal(h.calls[1].options.emailRedirectTo,plan==='free'?'https://stockradar.vn/':'https://stockradar.vn/thanh-toan/?plan=premium');
    assert.equal(body.session,undefined);
  }
});
test('signup fails closed if verification is disabled and preserves Auth throttling',async()=>{
  const h=signup({autoConfirm:true});assert.equal((await h.run()).status,503);assert.equal(h.calls.length,0);
  assert.equal((await signup({error:{status:429}}).run()).status,429);
  assert.equal((await signup({session:{access_token:'fixture'}}).run()).status,409);
});

function checkout({idempotent=false,providerFailures=0,validHook=true}={}){
  let handler;const calls=[];let failures=providerFailures;
  const Deno={env:{get:n=>({SUPABASE_URL:'https://fixture.invalid',SUPABASE_ANON_KEY:'public-fixture',SUPABASE_SERVICE_ROLE_KEY:'server-fixture'}[n])},serve:fn=>handler=fn};
  const result={checkout_id:'11111111-1111-4111-8111-111111111111',customer_email:'qa@example.invalid',approver_email:'admin@example.invalid',amount_vnd:199000,payment_reference:'TEST-LOCAL',plan_code:'ADVANCED_TEST',duration_days:30,approval_status:'PENDING',approval_expires_at:'2026-09-07T00:00:00Z',confirmed_at:'2026-09-06T00:00:00Z',should_send:true};
  const fetch=async(url,args)=>{calls.push({url,body:JSON.parse(args.body),headers:args.headers});let value;
    if(url.includes('verify_stockradar'))value=validHook;
    else if(url.includes('inspect_stockradar')||url.includes('prepare_stockradar'))value=result;
    else if(url.includes('resolve_stockradar'))value={...result,approval_status:'APPROVED',paid_until:'2026-10-06T00:00:00Z',idempotent};
    else if(url.includes('get_stockradar_email_provider'))value={api_key:'fixture-provider',from_address:'admin@example.invalid'};
    else if(url.includes('api.resend.com')){if(failures-->0)return new Response('{}',{status:503});value={id:'provider-fixture'};}
    else value=true;
    return new Response(JSON.stringify(value));
  };
  const source=fs.readFileSync(new URL('../../supabase/functions/checkout-approval/index.ts',import.meta.url),'utf8').replace(/^import .*;\r?\n/gm,'');
  new Function('Deno','fetch',stripTypeScriptTypes(source))(Deno,fetch);
  return {calls,run:req=>handler(req),notify:()=>handler(new Request('https://fixture.invalid/functions/v1/checkout-approval',{method:'POST',headers:{'content-type':'application/json','x-stockradar-checkout-hook':'fixture-hook-secret'.repeat(4)},body:JSON.stringify({action:'notify',checkout_id:result.checkout_id})}))};
}
const url='https://fixture.invalid/functions/v1/checkout-approval';
test('opening approval link is read-only and has private non-embeddable response',async()=>{
  const h=checkout(),r=await h.run(new Request(`${url}?token=${'A'.repeat(43)}&decision=APPROVE`)),html=await r.text();
  assert.equal(r.status,200);assert.match(html,/form method="post"/);
  assert.match(html,/XÁC NHẬN ĐÃ NHẬN TIỀN/);
  assert.equal(h.calls.length,1);assert.match(h.calls[0].url,/inspect_stockradar/);
  assert.equal(r.headers.get('referrer-policy'),'no-referrer');assert.equal(r.headers.get('x-frame-options'),'DENY');
  assert.equal(r.headers.get('x-robots-tag'),'noindex, nofollow');
});
test('notify uses Vault, one stable link/idempotency key and no payment mutation',async()=>{
  const h=checkout({providerFailures:1});assert.equal((await h.notify()).status,202);assert.equal((await h.notify()).status,202);
  const sends=h.calls.filter(c=>c.url.includes('api.resend.com'));
  assert.equal(sends.length,3);
  assert.equal(new Set(sends.map(c=>c.headers['Idempotency-Key'])).size,1);
  assert.equal(new Set(sends.map(c=>JSON.stringify(c.body))).size,1);
  assert.match(sends[0].body.html,/Thời gian khách báo chuyển khoản/);assert.match(sends[0].body.html,/CHỜ QUẢN TRỊ XÁC NHẬN TIỀN/);
  assert.ok(!h.calls.some(c=>c.url.includes('resolve_stockradar')));
});
test('final POST resolves once; repeated approval does not send another customer email',async()=>{
  for(const idempotent of [false,true]){
    const h=checkout({idempotent});const r=await h.run(new Request(url,{method:'POST',headers:{'content-type':'application/x-www-form-urlencoded'},body:new URLSearchParams({action:'decision',token:'A'.repeat(43),decision:'APPROVE'})}));
    assert.equal(r.status,200);
    assert.equal(h.calls.filter(c=>c.url.includes('resolve_stockradar')).length,1);
    assert.equal(h.calls.filter(c=>c.url.includes('api.resend.com')).length,idempotent?0:1);
  }
});
test('untrusted hooks and malformed links cannot send or grant',async()=>{
  const h=checkout({validHook:false});assert.equal((await h.notify()).status,401);
  assert.ok(!h.calls.some(c=>c.url.includes('api.resend.com')));
  assert.equal((await h.run(new Request(url+'?token=bad&decision=APPROVE'))).status,400);
});
