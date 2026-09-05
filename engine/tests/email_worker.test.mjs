import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {stripTypeScriptTypes} from 'node:module';
import {actionBody,dailyBody} from '../../supabase/functions/_shared/email-copy.ts';
function harness({auth=true,preflight=true,items=[]}={}){
  let handler;const calls=[];
  const Deno={env:{get:name=>({SUPABASE_URL:'https://fixture.invalid',SUPABASE_SECRET_KEYS:'{"default":"sb_secret_fixture_only"}'}[name])},serve:fn=>handler=fn};
  const fetch=async(url,args)=>{calls.push({url,body:JSON.parse(args.body)});let value;
    if(url.includes('/rpc/verify_'))value=auth;
    else if(url.includes('get_stockradar_email_provider_config'))value={api_key:'test-provider-secret',from_address:'StockRadar <fixture@example.invalid>'};
    else if(url.includes('claim_stockradar'))value=items;
    else if(url.includes('preflight_stockradar'))value={allowed:preflight};
    else if(url.includes('issue_stockradar'))value='test-token';
    else if(url.includes('api.resend.com'))value={id:'provider-test-id'};
    else value={};return new Response(JSON.stringify(value));};
  const source=fs.readFileSync(new URL('../../supabase/functions/email-worker/index.ts',import.meta.url),'utf8').replace(/^import .*;\r?\n/gm,'');
  new Function('Deno','fetch','actionBody','dailyBody',stripTypeScriptTypes(source))(Deno,fetch,actionBody,dailyBody);
  return {calls,async run(body={},token='a'.repeat(64)){return handler(new Request('https://fixture.invalid',{method:'POST',headers:token?{'x-stockradar-scheduler':token}:{},body:JSON.stringify(body)}));}};
}
test('health requires authentication, reveals booleans only and never claims email',async()=>{
  const denied=harness({auth:false});assert.equal((await denied.run({mode:'health'})).status,401);
  assert.equal(denied.calls.length,1);
  const allowed=harness();const r=await allowed.run({mode:'health'}),b=await r.json();
  assert.deepEqual(b,{ok:true,provider_configured:true,sender_configured:true});
  assert.ok(!allowed.calls.some(x=>/claim_stockradar|api.resend.com/.test(x.url)));
});
test('revoked eligibility stops provider delivery after a claim',async()=>{
  const h=harness({preflight:false,items:[{outbox_id:'id',user_id:'uid',recipient_email:'test@example.invalid',email_kind:'DAILY_BRIEF',idempotency_key:'idempotency'}]});
  const b=await (await h.run()).json();assert.equal(b.sent,0);assert.equal(b.suppressed,1);
  assert.ok(!h.calls.some(x=>/api.resend.com|issue_stockradar/.test(x.url)));
});
test('eligible delivery uses the concrete report and records provider acceptance',async()=>{
  const h=harness({items:[{outbox_id:'id',user_id:'uid',recipient_email:'test@example.invalid',email_kind:'EVENT_ALERT',idempotency_key:'idempotency',payload:{ticker:'ZZZ',previous_state:'WAIT',current_state:'BUY',decision_card:{ticker:'ZZZ',reference_price:20000,buy_zone:[19800,20100],stop:18500,target:24000,evaluated_at:'2026-09-04T03:30:00Z'}}}]});
  const b=await (await h.run()).json();assert.equal(b.sent,1);
  const send=h.calls.find(x=>x.url.includes('api.resend.com')).body;
  assert.match(send.html,/20.000đ/);assert.match(send.html,/10:30/);assert.match(send.html,/Ngừng toàn bộ email/);
  assert.equal(h.calls.at(-1).body.p_result,'SENT');assert.equal(h.calls.at(-1).body.p_provider_message_id,'provider-test-id');
});
