"""Exact-source patch: owned context reads and honest knowledge-provider status."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MARK='// PROJECT_CONTEXT_READ_V1'
def once(s,a,b):
    if s.count(a)!=1: raise RuntimeError(f'Source drift: {s.count(a)} matches for {a[:90]!r}')
    return s.replace(a,b,1)

def patch_chat(s):
    if MARK in s: return s
    s=MARK+'\nimport { projectRecordIntent, projectRecordAnswer, knowledgeProviderFailure } from "../_shared/chat-continuation.ts";\n'+s
    s=once(s,'knowledge_version,created_at")','knowledge_version,metadata,created_at")')
    s=once(s,'source:result?.source || null,project_bridge:result?.project_bridge || null','source:result?.source || null,project_bridge:result?.project_bridge || null,reason:result?.reason || null,provider_attempted:result?.provider_attempted ?? null,provider_http_status:result?.provider_http_status ?? null,quota_consumed:result?.quota_consumed ?? null')
    start=s.index('async function knowledgeAnswer(')
    end=s.index('\nDeno.serve(',start)
    old=s[start:end]
    old=once(old,'if (!quotaResult.ok) return {httpStatus:quotaResult.status, payload:{...quotaResult.body,thread_id:thread.id,knowledge_version:knowledge.version}};','if (!quotaResult.ok) return {httpStatus:quotaResult.status, payload:{...quotaResult.body,thread_id:thread.id,knowledge_version:knowledge.version,quota_consumed:false,provider_attempted:false,model_status:"MODEL_NOT_CALLED"}};\n  const base = {tier,scope:"conversation",mode:"KNOWLEDGE_ONLY",thread_id:thread.id,...projectKnowledgeMeta(knowledge,false),quota:quotaResult.quota,quota_consumed:true};\n  const fallback = (failure: any) => ({httpStatus:200,payload:{...base,status:"READY_FALLBACK",answer_engine:"KNOWLEDGE_CORE",...failure}});')
    a=old.index('  if (!key) return ');z=old.index('\n  const instructions =',a)
    old=old[:a]+'  if (!key) return fallback(knowledgeProviderFailure({kind:"MISSING_KEY"}));'+old[z:]
    a=old.index('  } catch (error) {');z=old.index('\n  let payload:',a)
    old=old[:a]+'''  } catch (error) {
    return fallback(knowledgeProviderFailure({kind:error?.name === "TimeoutError" ? "TIMEOUT" : "NETWORK"}));
  }'''+old[z:]
    a=old.index('  if (!text) return ');z=old.index('\n}',a)
    old=old[:a]+'''  if (!text) return fallback(knowledgeProviderFailure({status:response.status,payload}));
  return {httpStatus:200,payload:{...base,status:"READY",model_status:"MODEL_READY",answer_engine:"MODEL_PLUS_KNOWLEDGE_CORE",...projectKnowledgeMeta(knowledge,true),provider_attempted:true,provider_http_status:response.status,answer:text}};'''+old[z:]
    s=s[:start]+old+s[end:]
    anchor='    const existing = await loadMessages(db,thread.id,MAX_STORED_HISTORY);'
    insert='''    // Read only the server-reviewed record. Never use this branch for market analysis.
    const recordIntent = explicitTicker(message) ? null : projectRecordIntent(message);
    if (recordIntent) {
      const {data:burst,error:burstError} = await db.rpc("consume_stockradar_api_quota",{p_user_id:user.id,p_bucket:"stock_ai_burst"});
      if (burstError || !burst || burst.reason === "POLICY_MISSING") return json({status:"SERVICE_UNAVAILABLE",reason:"AI_BURST_POLICY_UNAVAILABLE",quota_consumed:false,provider_attempted:false},503,origin);
      if (burst.allowed !== true) return json({status:"RATE_LIMITED",reason:"TECHNICAL_RATE_LIMIT",tier,quota_consumed:false,provider_attempted:false,answer:"Bạn đang gửi nhiều yêu cầu liên tiếp. Vui lòng thử lại sau một phút."},429,origin);
      const record = {...projectRecordAnswer(projectBridge,thread.id,recordIntent),...projectKnowledgeMeta(knowledge,false),tier,thread_id:thread.id,project_bridge:projectBridgeMeta(projectBridge,thread.id,false)};
      await saveExchange(db,thread,{message,scope:"conversation",ticker:"",horizon:thread.last_horizon || "SHORT_TERM"},record,knowledge.version);
      return json({...record,conversation_persisted:true},200,origin);
    }
'''
    s=once(s,anchor,insert+anchor)
    s=once(s,'await saveExchange(db,thread,{message,scope:"conversation",ticker:"",horizon:inputHorizon},result.payload,knowledge.version);','await saveExchange(db,thread,{message,scope:"conversation",ticker:"",horizon:inputHorizon},result.payload,knowledge.version);\n        result.payload.conversation_persisted = true;')
    return s

def patch_tests(s):
    if MARK in s: return s
    s=MARK+"\nimport * as continuation from '../../supabase/functions/_shared/chat-continuation.ts';\n"+s
    s=once(s,'function harness({user=U,providerError=false,linked=true}={})','function harness({user=U,providerError=false,linked=true,keyMissing=false,burstAllowed=true}={})')
    s=once(s,"OPENAI_API_KEY:'test'","OPENAI_API_KEY:keyMissing?'':'test'")
    s=once(s,'...bridge,...knowledge,Deno','...bridge,...knowledge,...continuation,Deno')
    s=once(s,'return {data:{allowed:true,unlimited:true,limit:null,remaining:null}};','return {data:{allowed:args?.p_bucket === "stock_ai_burst" ? burstAllowed : true,unlimited:true,limit:null,remaining:null}};')
    s=once(s,'return {calls,get modelInput()','return {calls,tables,get modelInput()')
    s=once(s,"const h=harness();await h.ask({message:'Đoạn chat này liên thông với dự án của tôi chưa?',thread_id:T});\n assert.equal(h.forwarded,undefined);assert.equal(h.modelInput.PROJECT_HANDOFF.summary,SUMMARY);","const h=harness();const r=await h.ask({message:'Đoạn chat này liên thông với dự án của tôi chưa?',thread_id:T});\n assert.equal(h.forwarded,undefined);assert.equal(h.modelInput,undefined);assert.equal(r.body.model_status,'MODEL_NOT_CALLED');assert.equal(r.body.project_bridge.context_loaded,true);assert.equal(r.body.project_bridge.context_applied,false);")
    s+='''

test('project record status remains available without a configured model and consumes no daily question',async()=>{
 const h=harness({keyMissing:true});const r=await h.ask({message:'Đã liên thông với dự án chưa?',thread_id:T});
 assert.equal(r.status,200);assert.equal(r.body.answer_engine,'PROJECT_HANDOFF_RECORD');assert.equal(r.body.quota_consumed,false);assert.equal(r.body.provider_attempted,false);assert.equal(r.body.conversation_persisted,true);
 assert.match(r.body.answer,/PRIVATE_TEST_V1/);assert.ok(!r.body.answer.includes(SUMMARY));assert.equal(h.modelInput,undefined);
 assert.equal(h.calls.filter(x=>x.name==='consume_stockradar_api_quota'&&x.args.p_bucket==='stock_ai').length,0);
 assert.equal(h.calls.filter(x=>x.name==='consume_stockradar_api_quota'&&x.args.p_bucket==='stock_ai_burst').length,1);
});
test('project summary reads only the owned record and ignores forged client content',async()=>{
 const h=harness({keyMissing:true});const r=await h.ask({message:'Xem ngữ cảnh dự án đã chuyển',thread_id:T,project_context:'FORGED_SUMMARY'});
 assert.match(r.body.answer,/PRIVATE_REVIEWED_HANDOFF_ONLY_FOR_OWNER/);assert.ok(!r.body.answer.includes('FORGED_SUMMARY'));assert.equal(r.body.model_status,'MODEL_NOT_CALLED');assert.equal(h.modelInput,undefined);
});
test('an unrelated account cannot obtain the project record in its own thread',async()=>{
 const h=harness({user:V});const r=await h.ask({message:'Xem ngữ cảnh dự án đã chuyển',thread_id:O,user_id:U});
 assert.equal(r.status,200);assert.ok(!r.body.answer.includes(SUMMARY));assert.equal(r.body.project_bridge.available,false);assert.equal(h.modelInput,undefined);
});
test('record reads retain technical throttling without consuming daily questions',async()=>{
 const h=harness({burstAllowed:false});const r=await h.ask({message:'Đã liên thông với dự án chưa?',thread_id:T});
 assert.equal(r.status,429);assert.equal(r.body.reason,'TECHNICAL_RATE_LIMIT');assert.equal(r.body.quota_consumed,false);assert.equal(h.modelInput,undefined);assert.equal(h.tables.stockradar_ai_messages.length,1);
});
test('knowledge credit failure is specific, persisted and never claims knowledge application',async()=>{
 const h=harness({providerError:true});const r=await h.ask({message:'SEPA là gì?',thread_id:T});
 assert.equal(r.body.model_status,'MODEL_CREDIT_BLOCKED');assert.equal(r.body.reason,'OPENAI_429_QUOTA_EXHAUSTED');assert.equal(r.body.provider_http_status,429);assert.equal(r.body.provider_attempted,true);assert.equal(r.body.knowledge_applied,false);assert.equal(r.body.conversation_persisted,true);
 assert.match(r.body.answer,/không phải hết lượt hỏi/);const saved=h.tables.stockradar_ai_messages.find(x=>x.role==='assistant');assert.equal(saved.metadata.reason,'OPENAI_429_QUOTA_EXHAUSTED');
});
test('missing key cannot be misreported as exhausted credit or successful provider attempt',async()=>{
 const h=harness({keyMissing:true});const r=await h.ask({message:'SEPA là gì?',thread_id:T});
 assert.equal(r.body.model_status,'MODEL_ERROR');assert.equal(r.body.reason,'OPENAI_KEY_MISSING');assert.equal(r.body.provider_attempted,false);assert.equal(r.body.knowledge_applied,false);assert.equal(r.body.project_bridge.context_applied,false);assert.equal(h.modelInput,undefined);
});
test('a successful knowledge model reply records true persistence only after saving',async()=>{
 const h=harness();const r=await h.ask({message:'SEPA là gì?',thread_id:T});
 assert.equal(r.body.model_status,'MODEL_READY');assert.equal(r.body.knowledge_applied,true);assert.equal(r.body.conversation_persisted,true);assert.equal(r.body.provider_http_status,200);assert.equal(h.tables.stockradar_ai_messages.length,3);
});
'''
    return s

if __name__=='__main__':
    changes={
      ROOT/'supabase/functions/stock-ai-chat/index.ts':patch_chat,
      ROOT/'engine/tests/private_project_chat.test.mjs':patch_tests,
    }
    prepared={p:fn(p.read_text(encoding='utf-8')) for p,fn in changes.items()}
    for p,text in prepared.items(): p.write_text(text,encoding='utf-8')
    print('Owned context reads and knowledge diagnostics patched; no schema, key or entitlement changes.')
