"""Apply fail-closed execution-mode gates; preserve legacy API paths for explicit rollback/testing."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MARK='// CHATGPT_WORKSPACE_NO_API_V1'
IMPORT='import { chatGPTWorkspaceMode, chatGPTWorkspaceHandoff } from "../_shared/chatgpt-workspace.ts";\n'
def once(s,a,b):
    if s.count(a)!=1:raise RuntimeError(f'Source drift: {s.count(a)} matches {a[:100]!r}')
    return s.replace(a,b,1)
def research(s):
    if MARK in s:return s
    s=MARK+'\n'+IMPORT+s
    return once(s,'  const query=parseResearchQuery(message,requestedTicker);','  if(chatGPTWorkspaceMode(Deno.env)){if(!message||!validHorizon(horizon))return json({status:"INVALID_REQUEST"},400,origin);return json(chatGPTWorkspaceHandoff(message,horizon),200,origin);}\n  const query=parseResearchQuery(message,requestedTicker);')
def chat(s):
    if MARK in s:return s
    s=MARK+'\n'+IMPORT+s
    s=once(s,'  const quotaResult = await consumeKnowledgeQuota(db,userId,tier);','  if (chatGPTWorkspaceMode(Deno.env)) return {httpStatus:200,payload:chatGPTWorkspaceHandoff(message,inputHorizon)};\n  const quotaResult = await consumeKnowledgeQuota(db,userId,tier);')
    s=once(s,'    const existing = await loadMessages(db,thread.id,MAX_STORED_HISTORY);','    if (chatGPTWorkspaceMode(Deno.env)) return json({...chatGPTWorkspaceHandoff(message,body.horizon),thread_id:thread.id},200,origin);\n    const existing = await loadMessages(db,thread.id,MAX_STORED_HISTORY);')
    return s
def status(s):
    if MARK in s:return s
    s=MARK+'\n'+s
    return once(s,'export function withModelStatus(body: Record<string, any>) {','export function withModelStatus(body: Record<string, any>) {\n  if (body.mode === "CHATGPT_WORKSPACE") return {...body,model_status:"MODEL_NOT_CALLED",model_notice:null};')
def handlers(s):
    if MARK in s:return s
    s=MARK+"\nimport * as workspaceModeHelpers from '../../supabase/functions/_shared/chatgpt-workspace.ts';\n"+s
    s=once(s,'function harness({guest=false,','function harness({workspaceMode=false,guest=false,')
    s=once(s,"OPENAI_API_KEY:'test-only'","STOCKRADAR_INFERENCE_MODE:workspaceMode?'CHATGPT_WORKSPACE':'API',OPENAI_API_KEY:'test-only'")
    s=once(s,'...privateProjectContext,Deno','...privateProjectContext,...workspaceModeHelpers,Deno')
    s+='''\n\ntest('workspace mode stops signed-in and guest API inference before quota or market queries',async()=>{for(const guest of [false,true]){const h=harness({guest,workspaceMode:true});const r=await h.ask('Phân tích FPT');assert.equal(r.status,200);assert.equal(r.body.mode,'CHATGPT_WORKSPACE');assert.equal(r.body.model_status,'MODEL_NOT_CALLED');assert.equal(r.body.provider_attempted,false);assert.equal(r.body.quota_consumed,false);assert.equal(h.modelInput,undefined);assert.equal(h.quotaCalls,0);assert.ok(!h.calls.some(x=>x.name==='fetch_stockradar_ai_context'));assert.equal(r.body.handoff.url,'https://chatgpt.com/');}});\n'''
    return s
def private_tests(s):
    if MARK in s:return s
    s=MARK+"\nimport * as workspaceModeHelpers from '../../supabase/functions/_shared/chatgpt-workspace.ts';\n"+s
    s=once(s,'function harness({user=U,','function harness({workspaceMode=false,user=U,')
    s=once(s,"OPENAI_API_KEY:keyMissing?'':'test'","STOCKRADAR_INFERENCE_MODE:workspaceMode?'CHATGPT_WORKSPACE':'API',OPENAI_API_KEY:keyMissing?'':'test'")
    s=once(s,'...continuation,Deno','...continuation,...workspaceModeHelpers,Deno')
    s+='''\n\ntest('workspace chat never calls inference or daily quota for a new research/method question',async()=>{for(const message of ['Phân tích FPT','SEPA là gì?']){const h=harness({workspaceMode:true});const r=await h.ask({message,thread_id:T});assert.equal(r.body.mode,'CHATGPT_WORKSPACE');assert.equal(r.body.provider_attempted,false);assert.equal(h.modelInput,undefined);assert.equal(h.forwarded,undefined);assert.ok(!h.calls.some(x=>x.name==='consume_stockradar_api_quota'));assert.equal(h.tables.stockradar_ai_messages.length,1);}});\ntest('workspace mode preserves owned history and context record reads',async()=>{const h=harness({workspaceMode:true});assert.equal((await h.ask({operation:'history',thread_id:T})).body.messages.length,1);const r=await h.ask({message:'Đã liên thông với dự án chưa?',thread_id:T});assert.equal(r.body.answer_engine,'PROJECT_HANDOFF_RECORD');assert.equal(r.body.provider_attempted,false);});\n'''
    return s
def workflow(s):
    if '# CHATGPT_WORKSPACE_FINAL_STAGE' in s:return s
    anchor='      - name: Configure GitHub Pages\n'
    new='''      # CHATGPT_WORKSPACE_FINAL_STAGE — legacy compatibility checked above; verify delivered mode below.
      - name: Activate and verify ChatGPT workspace without billable inference
        run: |
          python scripts/activate_chatgpt_workspace.py .pages-site
          python -m http.server 8766 --bind 127.0.0.1 --directory .pages-site >/tmp/workspace-http.log 2>&1 &
          server_pid=$!
          trap 'kill "$server_pid" 2>/dev/null || true' EXIT
          for attempt in {1..30}; do curl -fsS http://127.0.0.1:8766/ >/dev/null && break; sleep 0.2; done
          STOCKRADAR_QA_URL=http://127.0.0.1:8766 node scripts/chatgpt_workspace_qa.cjs
'''
    return once(s,anchor,new+anchor)
if __name__=='__main__':
    f={'supabase/functions/stock-ai/index.ts':research,'supabase/functions/stock-ai-guest/index.ts':research,'supabase/functions/stock-ai-chat/index.ts':chat,'supabase/functions/_shared/model-status.ts':status,'engine/tests/ai_handlers.test.mjs':handlers,'engine/tests/private_project_chat.test.mjs':private_tests,'.github/workflows/pages.yml':workflow}
    prepared={p:fn((ROOT/p).read_text()) for p,fn in f.items()}
    for p,s in prepared.items():(ROOT/p).write_text(s)
    print('Workspace mode gates and final Pages stage prepared. No key, entitlement or email changes.')
