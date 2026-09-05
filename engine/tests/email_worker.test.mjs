import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {stripTypeScriptTypes} from 'node:module';
import {actionBody,dailyBody,emailPricePlanError,emailSubject} from '../../supabase/functions/_shared/email-copy.ts';
test('action subject and first heading carry setup, Vietnam time, price and canonical sizing',()=>{
  const payload={decision_card:{ticker:'ZZZ',setup:'EARLY_BREAKOUT',current_state:'BUY',reference_price:20100,evaluated_at:'2026-09-04T04:15:00Z',position_initial_pct:25}};
  assert.equal(emailSubject(payload,'EVENT_ALERT'),'[EARLY BREAKOUT] ZZZ — 11:15 04/09/2026 — Giá 20.100đ');
  assert.match(actionBody(payload,'https://fixture.invalid'),/^<h1[^>]*>HÀNH ĐỘNG: MUA THĂM DÒ 25%/);
  assert.match(actionBody(payload,'https://fixture.invalid'),/Phân tích chi tiết bằng AI StockRadar/);
  assert.match(emailSubject({...payload,decision_card:{...payload.decision_card,current_state:'SELL'}},'EVENT_ALERT'),/^\[BÁN\]/);
  assert.equal(emailPricePlanError({decision_card:{current_state:'TĂNG'}},'EVENT_ALERT'),'BUY_EMAIL_MISSING_TARGET_STOP_OR_ENTRY');
});
function harness({auth=true,preflight=true,preflightPayload=null,items=[]}={}){
  let handler;const calls=[];
  const Deno={env:{get:name=>({SUPABASE_URL:'https://fixture.invalid',SUPABASE_SECRET_KEYS:'{"default":"sb_secret_fixture_only"}'}[name])},serve:fn=>handler=fn};
  const fetch=async(url,args)=>{calls.push({url,body:JSON.parse(args.body)});let value;
    if(url.includes('/rpc/verify_'))value=auth;
    else if(url.includes('get_stockradar_email_provider_config'))value={api_key:'test-provider-secret',from_address:'StockRadar <fixture@example.invalid>'};
    else if(url.includes('claim_stockradar'))value=items;
    else if(url.includes('preflight_stockradar'))value={allowed:preflight,...(preflightPayload?{payload:preflightPayload}:{})};
    else if(url.includes('issue_stockradar'))value='test-token';
    else if(url.includes('api.resend.com'))value={id:'provider-test-id'};
    else value={};return new Response(JSON.stringify(value));};
  const source=fs.readFileSync(new URL('../../supabase/functions/email-worker/index.ts',import.meta.url),'utf8').replace(/^import .*;\r?\n/gm,'');
  new Function('Deno','fetch','actionBody','dailyBody','emailPricePlanError','emailSubject',stripTypeScriptTypes(source))(Deno,fetch,actionBody,dailyBody,emailPricePlanError,emailSubject);
  return {calls,async run(body={},token='a'.repeat(64)){return handler(new Request('https://fixture.invalid',{method:'POST',headers:token?{'x-stockradar-scheduler':token}:{},body:JSON.stringify(body)}));}};
}
test('health requires authentication, reveals booleans only and never claims email',async()=>{
  const denied=harness({auth:false});assert.equal((await denied.run({mode:'health'})).status,401);
  assert.equal(denied.calls.length,1);
  const allowed=harness();const r=await allowed.run({mode:'health'}),b=await r.json();
  assert.deepEqual(b,{ok:true,provider_configured:true,sender_configured:true});
  assert.ok(!allowed.calls.some(x=>/claim_stockradar|api.resend.com/.test(x.url)));
});

test('buy email missing a stop or correct horizon target is suppressed before provider submission',async()=>{
  for(const card of [{current_state:'BUY',buy_zone:[20000,20100],target:24000},{current_state:'ADD',horizon:'LONG_TERM',buy_zone:[20000,20100],stop_loss:19000,target_near:24000}]){
    const h=harness({items:[{outbox_id:'id',user_id:'uid',recipient_email:'test@example.invalid',email_kind:'EVENT_ALERT',idempotency_key:'idempotency',payload:{decision_card:card}}]});
    const b=await(await h.run()).json();assert.equal(b.sent,0);assert.equal(b.suppressed,1);
    assert.ok(!h.calls.some(x=>/api.resend.com|issue_stockradar/.test(x.url)));
  }
});

test('canonical preflight prices override older queued targets in delivered HTML',async()=>{
  const card={ticker:'ZZZ',current_state:'BUY',horizon:'LONG_TERM',setup:'EARLY_BREAKOUT',position_initial_pct:25,risk_reward:2,buy_zone:[20000,20100],stop_loss:18500,target_near:24000,target_3_6m:28000,target_12m:32000};
  const h=harness({preflightPayload:{decision_card:card},items:[{outbox_id:'id',user_id:'uid',recipient_email:'test@example.invalid',email_kind:'EVENT_ALERT',idempotency_key:'idempotency',payload:{decision_card:{...card,target_12m:999999}}}]});
  const b=await(await h.run()).json();assert.equal(b.sent,1);
  const email=h.calls.find(x=>/api.resend.com/.test(x.url)).body.html;
  for(const value of ['18.500đ','24.000đ','28.000đ','32.000đ'])assert.ok(email.includes(value),value);
  assert.doesNotMatch(email,/999\.999/);
});
test('revoked eligibility stops provider delivery after a claim',async()=>{
  const h=harness({preflight:false,items:[{outbox_id:'id',user_id:'uid',recipient_email:'test@example.invalid',email_kind:'DAILY_BRIEF',idempotency_key:'idempotency'}]});
  const b=await (await h.run()).json();assert.equal(b.sent,0);assert.equal(b.suppressed,1);
  assert.ok(!h.calls.some(x=>/api.resend.com|issue_stockradar/.test(x.url)));
});
test('eligible delivery uses the concrete report and records provider acceptance',async()=>{
  const h=harness({items:[{outbox_id:'id',user_id:'uid',recipient_email:'test@example.invalid',email_kind:'EVENT_ALERT',idempotency_key:'idempotency',payload:{ticker:'ZZZ',previous_state:'WAIT',current_state:'BUY',decision_card:{ticker:'ZZZ',setup:'EARLY_BREAKOUT',position_initial_pct:25,risk_reward:2,reference_price:20000,buy_zone:[19800,20100],stop:18500,target:24000,evaluated_at:'2026-09-04T03:30:00Z'}}}]});
  const b=await (await h.run()).json();assert.equal(b.sent,1);
  const send=h.calls.find(x=>x.url.includes('api.resend.com')).body;
  assert.match(send.html,/20.000đ/);assert.match(send.html,/10:30/);assert.match(send.html,/Ngừng toàn bộ email/);
  assert.equal(h.calls.at(-1).body.p_result,'SENT');assert.equal(h.calls.at(-1).body.p_provider_message_id,'provider-test-id');
});
