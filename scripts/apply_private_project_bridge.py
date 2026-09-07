"""Exact, atomic, idempotent patch for reviewed private project handoffs."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
MARK = '// PRIVATE_PROJECT_BRIDGE_V1'
IMPORT = 'import { loadProjectBridge, loadProjectContext, projectContextInput, projectBridgeMeta, PROJECT_HANDOFF_RULE } from "../_shared/stockradar-project-context.ts";\n'
MASK = r".replace(/\btra\s+(?:cứu|cuu)(?=\s|$|[.,:;!?])/giu,' ')"

def once(s, old, new):
    if s.count(old) != 1:
        raise RuntimeError(f'Source drift ({s.count(old)} matches): {old[:95]}')
    return s.replace(old,new,1)

def patch_chat(s):
    s = IMPORT + MARK + '\n' + s
    s = once(s,'text.toUpperCase().match(',f'text{MASK}.toUpperCase().match(')
    a=s.index('  if (!forceNew && UUID_RE.test(requested)) {')
    z=s.index('  if (!forceNew) {',a)
    s=s[:a]+'''  if (!forceNew && requested) {
    if (!UUID_RE.test(requested)) throw new Error("INVALID_THREAD_ID");
    const {data,error} = await db.from("stockradar_ai_threads").select("*").eq("id",requested).eq("user_id",userId).eq("status","ACTIVE").maybeSingle();
    if (error) throw new Error("THREAD_READ_FAILED");
    if (!data) throw new Error("THREAD_NOT_FOUND");
    return data;
  }
'''+s[z:]
    s=once(s,'if (!["ask","history","new_thread"].includes(operation))','if (!["ask","history","new_thread"].includes(operation) && !["project_bridge","resume_project"].includes(operation))')
    s=once(s,'    if (operation === "new_thread") {','''    const projectBridge = await loadProjectBridge(db,user.id);
    if (operation === "project_bridge") return json({status:"READY",project_bridge:projectBridgeMeta(projectBridge),knowledge_version:knowledge.version},200,origin);
    if (operation === "resume_project") {
      if (!projectBridge) return json({status:"NOT_FOUND",reason:"PROJECT_BRIDGE_NOT_LINKED"},404,origin);
      const linked = await ensureThread(db,user.id,projectBridge.thread_id,knowledge.version,false);
      const messages = await loadMessages(db,linked.id,40);
      return json({status:"READY",thread_id:linked.id,title:linked.title,project_bridge:projectBridgeMeta(projectBridge,linked.id),knowledge_version:knowledge.version,messages},200,origin);
    }
    if (operation === "new_thread") {''')
    s=once(s,'knowledge_version:knowledge.version,messages:[]','knowledge_version:knowledge.version,project_bridge:projectBridgeMeta(projectBridge,thread.id),messages:[]')
    s=once(s,'title:thread.title || null,knowledge_version:knowledge.version,messages},200','title:thread.title || null,knowledge_version:knowledge.version,project_bridge:projectBridgeMeta(projectBridge,thread.id),messages},200')
    s=once(s,'thread: any, inputHorizon: string) {','thread: any, inputHorizon: string, bridge: any) {')
    s=once(s,'", knowledge);','", knowledge) + (projectContextInput(bridge,thread.id) ? PROJECT_HANDOFF_RULE : "");')
    s=once(s,'const context = {USER_QUESTION:message,','const context = {PROJECT_HANDOFF:projectContextInput(bridge,thread.id),USER_QUESTION:message,')
    s=once(s,'message,existing,knowledge,thread,inputHorizon);','message,existing,knowledge,thread,inputHorizon,projectBridge);\n      result.payload = {...result.payload,project_bridge:projectBridgeMeta(projectBridge,thread.id,result.payload?.model_status === "MODEL_READY")};')
    s=once(s,'    const forward = {\n      scope,','    const forward = {\n      thread_id:thread.id,\n      scope,')
    s=once(s,'metadata:{mode:result?.mode || null,status:result?.status || null,source:result?.source || null}','metadata:{mode:result?.mode || null,status:result?.status || null,source:result?.source || null,project_bridge:result?.project_bridge || null}')
    s=once(s,'    console.error("stock-ai-chat",error?.message || error);','''    if (error?.message === "THREAD_NOT_FOUND") return json({status:"NOT_FOUND",reason:"THREAD_NOT_FOUND"},404,origin);
    if (error?.message === "INVALID_THREAD_ID") return json({status:"INVALID_REQUEST",reason:"INVALID_THREAD_ID"},400,origin);
    console.error("stock-ai-chat","REQUEST_FAILED");''')
    return s

def patch_research(s):
    s=IMPORT+MARK+'\n'+s
    s=once(s,'  const projectKnowledge=await loadProjectKnowledge(db);','  const projectKnowledge=await loadProjectKnowledge(db);\n  const projectContext=await loadProjectContext(db,user.id,body.thread_id);')
    s=once(s,'  const base={...projectKnowledgeMeta(projectKnowledge),','  const base={project_bridge:projectBridgeMeta(projectContext,body.thread_id),...projectKnowledgeMeta(projectKnowledge),')
    s=once(s,'  const context={...fullResearchContext,','  const context={PROJECT_HANDOFF:projectContextInput(projectContext,body.thread_id),...fullResearchContext,')
    s=once(s,'instructions:projectKnowledgeInstructions(STOCKRADAR_SYSTEM_CORE,projectKnowledge),','instructions:projectKnowledgeInstructions(STOCKRADAR_SYSTEM_CORE,projectKnowledge)+(projectContext?PROJECT_HANDOFF_RULE:""),')
    s=once(s,'...base,...projectKnowledgeMeta(projectKnowledge,Boolean(modelText)),','...base,project_bridge:projectBridgeMeta(projectContext,body.thread_id,Boolean(modelText)),...projectKnowledgeMeta(projectKnowledge,Boolean(modelText)),')
    return s

def patch_client(s):
    s=MARK+'\n'+s
    s=once(s,"String(text || '').toUpperCase().match(",f"String(text || ''){MASK}.toUpperCase().match(")
    s=once(s,'    log.replaceChildren();\n    addMessage(log, \'assistant\', authenticated','    if (!authenticated && state.ui.projectResume) state.ui.projectResume.hidden = true;\n    log.replaceChildren();\n    addMessage(log, \'assistant\', authenticated')
    s=once(s,'    if (!response.ok) return false;','''    if (!response.ok) return false;
    const current = await authSession();
    if (!current?.user?.id || current.user.id !== session.user?.id) return false;
    if (state.ui.projectResume) {
      state.ui.projectResume.hidden = data.project_bridge?.available !== true;
      state.ui.projectResume.title = data.project_bridge?.available ? 'Mở cuộc trò chuyện có bản ngữ cảnh đã chuyển từ dự án ChatGPT. Không tự đọc mọi tin nhắn mới.' : '';
    }''')
    s=once(s,'      showIntro(log, true);\n      return true;','      state.history = [];\n      showIntro(log, true);\n      return true;')
    s=once(s,'    topLeft.append(threadToggle, status, continuity);','''    const projectResume = node('button', 'sr-center-new-chat', 'Tiếp tục từ dự án');
    projectResume.type = 'button';
    projectResume.hidden = true;
    topLeft.append(threadToggle, status, continuity, projectResume);''')
    s=once(s,'state.ui = { host, threadList, threadToggle, log, sideNewChat, newChat };','state.ui = { host, threadList, threadToggle, log, sideNewChat, newChat, projectResume };')
    s=once(s,"    threadToggle.addEventListener('click', toggleThreadDrawer);",'''    threadToggle.addEventListener('click', toggleThreadDrawer);
    projectResume.addEventListener('click', async () => {
      if (state.sending) return;
      state.sending = true;
      projectResume.disabled = true;
      try {
        const current = await currentAccountTier();
        if (!current.session?.access_token) return;
        const {response,data} = await callAuthenticated(current.session,{operation:'resume_project'});
        if (!response.ok || !data.thread_id) throw new Error('PROJECT_NOT_LINKED');
        await hydrateHistory(current.session,log,data.thread_id);
        await renderThreads(current.session,threadList,log);
        closeThreadDrawer();
      } catch (_) {
        addMessage(log,'assistant','Chưa mở được cuộc trò chuyện liên thông của tài khoản này.');
      } finally {
        state.sending = false;
        projectResume.disabled = false;
      }
    });''')
    return s

if __name__ == '__main__':
    targets={
      'supabase/functions/stock-ai-chat/index.ts':patch_chat,
      'supabase/functions/stock-ai/index.ts':patch_research,
      'website/assets/ai-center.js':patch_client,
      'supabase/functions/_shared/stockradar-query.ts':lambda s:MARK+'\n'+once(s,'message.toUpperCase().match(',f'message{MASK}.toUpperCase().match('),
      'engine/tests/ai_handlers.test.mjs':lambda s:MARK+'\n'+once(once(s,"import * as projectKnowledge from '../../supabase/functions/_shared/stockradar-knowledge.ts';","import * as projectKnowledge from '../../supabase/functions/_shared/stockradar-knowledge.ts';\nimport * as privateProjectContext from '../../supabase/functions/_shared/stockradar-project-context.ts';"),'...projectKnowledge,Deno','...projectKnowledge,...privateProjectContext,Deno'),
    }
    updates={path:fn((ROOT/path).read_text()) for path,fn in targets.items() if MARK not in (ROOT/path).read_text()}
    for path,text in updates.items(): (ROOT/path).write_text(text)
    print(f'Private project bridge: {len(updates)} exact-source updates; no secret or entitlement changes.')
