"""Idempotent source-anchored repair of private project chat continuity.
No changes to API keys, provider calls, account rights, database or stored history.
"""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
MARK = '// PROJECT_CHAT_CONTINUITY_V2'

def once(text, old, new):
    if text.count(old) != 1:
        raise RuntimeError(f'Source drift: {text.count(old)} matches for {old[:100]!r}')
    return text.replace(old,new,1)

def section(text,start,end,replacement):
    if text.count(start)!=1 or text.count(end)!=1:
        raise RuntimeError('Function boundary changed')
    a=text.index(start); z=text.index(end,a)
    return text[:a]+replacement+'\n\n'+text[z:]

def apply(text):
    if MARK in text: return text
    text=MARK+'\n'+text
    text=once(text,'    threadId: loadThreadId(),','    threadId: \'\',\n    accountId: \'\',\n    accountEpoch: 0,\n    historySequence: 0,\n    listSequence: 0,\n    hydrating: false,')
    text=section(text,'  function loadThreadId() {','  function validTicker(value) {',r'''  function loadThreadId(userId) {
    if (!/^[0-9a-f-]{36}$/i.test(String(userId || ''))) return '';
    try {
      const value = localStorage.getItem(`${THREAD_KEY}:${userId}`) || '';
      return /^[0-9a-f-]{36}$/i.test(value) ? value : '';
    } catch (_) { return ''; }
  }

  function saveThreadId(value) {
    if (!state.accountId) { state.threadId = ''; return; }
    state.threadId = /^[0-9a-f-]{36}$/i.test(String(value || '')) ? String(value) : '';
    try {
      const key = `${THREAD_KEY}:${state.accountId}`;
      if (state.threadId) localStorage.setItem(key, state.threadId);
      else localStorage.removeItem(key);
    } catch (_) {}
  }

  function bindAccount(session) {
    const userId = String(session?.user?.id || '');
    if (userId === state.accountId) return false;
    state.accountId = userId;
    state.accountEpoch += 1;
    state.historySequence += 1;
    state.listSequence += 1;
    state.hydrating = false;
    state.history = [];
    state.quota = null;
    state.threadId = loadThreadId(userId);
    // The old key had no owner. Recover from owned server history, not this pointer.
    try { localStorage.removeItem(THREAD_KEY); } catch (_) {}
    if (state.ui.projectResume) state.ui.projectResume.hidden = true;
    if (state.ui.continuity) state.ui.continuity.textContent = userId ? 'Đang mở hội thoại của tài khoản…' : 'Guest · ngữ cảnh tạm thời';
    state.ui.threadList?.replaceChildren();
    if (state.ui.log) showIntro(state.ui.log,Boolean(userId));
    return true;
  }

  async function sameAccount(session, epoch) {
    try {
      const current = await authSession();
      const userId = String(session?.user?.id || '');
      return state.accountEpoch === epoch && state.accountId === userId && String(current?.user?.id || '') === userId;
    } catch (_) { return false; }
  }

  function renderProjectMeta(data) {
    const bridge = data?.project_bridge;
    if (state.ui.projectResume) {
      state.ui.projectResume.hidden = !state.accountId || bridge?.available !== true;
      state.ui.projectResume.title = bridge?.available ? 'Mở hội thoại có ngữ cảnh đã chuyển từ dự án. Không tự đọc mọi tin nhắn mới trong ChatGPT.' : '';
    }
    if (state.ui.continuity) {
      const linked = bridge?.available === true && bridge.thread_id === state.threadId;
      state.ui.continuity.textContent = linked ? 'Hội thoại dự án đã mở' : state.accountId ? 'Đã lưu ngữ cảnh theo tài khoản' : 'Guest · ngữ cảnh tạm thời';
      state.ui.continuity.title = linked ? `Bản ngữ cảnh: ${String(bridge.version || '')}. Lưu hội thoại không đồng nghĩa mô hình AI đã phản hồi thành công.` : '';
    }
  }''')
    text=once(text,'    const session = await authSession();\n    const user = session?.user;','    const session = await authSession();\n    bindAccount(session);\n    const epoch = state.accountEpoch;\n    const user = session?.user;')
    text=once(text,"    const { data: profile, error } = await state.client.rpc('get_my_stockradar_access');\n    if (error) throw error;","    const { data: profile, error } = await state.client.rpc('get_my_stockradar_access');\n    if (!(await sameAccount(session,epoch))) throw new Error('ACCOUNT_CHANGED');\n    if (error) throw error;")
    text=section(text,'  async function hydrateHistory(','  function threadLabel(row) {',r'''  async function hydrateHistory(session, log, requestedThreadId = state.threadId, recoverMissing = false) {
    if (!session?.access_token) return false;
    const epoch = state.accountEpoch, sequence = ++state.historySequence;
    state.hydrating = true;
    try {
      if (!(await sameAccount(session,epoch))) return false;
      let {response,data} = await callAuthenticated(session,{operation: 'history',thread_id:requestedThreadId || null});
      if (sequence !== state.historySequence || !(await sameAccount(session,epoch))) return false;
      // Only implicit startup restoration may recover a removed/legacy thread.
      // An explicit sidebar selection is never silently replaced with another chat.
      if (recoverMissing && requestedThreadId && [400,404].includes(response.status) && ['THREAD_NOT_FOUND','INVALID_THREAD_ID'].includes(data.reason)) {
        saveThreadId('');
        ({response,data} = await callAuthenticated(session,{operation: 'history',thread_id:null}));
      }
      if (!response.ok || sequence !== state.historySequence || !(await sameAccount(session,epoch))) return false;
      const current = await authSession();
      if (!current?.user?.id || current.user.id !== session.user?.id || epoch !== state.accountEpoch || sequence !== state.historySequence) return false;
      if (!/^[0-9a-f-]{36}$/i.test(String(data.thread_id || ''))) return false;
      saveThreadId(data.thread_id);
      renderProjectMeta(data);
      const messages = Array.isArray(data.messages) ? data.messages : [];
      // Signed-in history lives on the server. Never put it in the Guest buffer.
      state.history = [];
      if (!messages.length) { showIntro(log,true); return true; }
      log.replaceChildren();
      messages.forEach(item => addMessage(log,item.role === 'user' ? 'user' : 'assistant',String(item.content || ''),item.scope === 'project_handoff' ? 'Bản tóm tắt chuyển từ dự án · không phải tin nhắn nguyên văn' : ''));
      return true;
    } finally {
      if (sequence === state.historySequence) state.hydrating = false;
    }
  }

  async function resumeProject(session, log) {
    const epoch = state.accountEpoch;
    if (!(await sameAccount(session,epoch))) return false;
    const {response,data} = await callAuthenticated(session,{operation:'resume_project'});
    if (!(await sameAccount(session,epoch))) return false;
    if (!response.ok || !data.thread_id) throw new Error('PROJECT_NOT_LINKED');
    return await hydrateHistory(session,log,data.thread_id);
  }''')
    text=once(text,'  async function renderThreads(session, list, log) {\n    if (!list) return;','  async function renderThreads(session, list, log) {\n    if (!list) return;\n    const epoch = state.accountEpoch, sequence = ++state.listSequence;')
    text=once(text,"    const { data, error } = await client.rpc('get_my_stockradar_ai_threads', { p_limit: 30 });\n    if (error)","    const { data, error } = await client.rpc('get_my_stockradar_ai_threads', { p_limit: 30 });\n    if (sequence !== state.listSequence || !(await sameAccount(session,epoch))) return;\n    if (error)")
    text=once(text,"""        if (state.sending || String(row.thread_id) === state.threadId) return;
        list.querySelectorAll('.sr-thread-item').forEach(el => el.classList.remove('is-active'));
        button.classList.add('is-active');
        saveThreadId(row.thread_id);
        await hydrateHistory(session, log, row.thread_id);
        closeThreadDrawer();""", """        if (state.sending || state.hydrating || String(row.thread_id) === state.threadId) return;
        state.sending = true;
        try {
          if (!(await sameAccount(session,epoch))) return;
          if (await hydrateHistory(session,log,row.thread_id)) {
            list.querySelectorAll('.sr-thread-item').forEach(el => el.classList.remove('is-active'));
            button.classList.add('is-active');
            closeThreadDrawer();
          }
        } finally { state.sending = false; }""")
    text=once(text,'    if (!session?.access_token || state.sending) return;\n    button.disabled = true;','    if (!session?.access_token || state.sending || state.hydrating) return;\n    const epoch = state.accountEpoch;\n    state.sending = true;\n    button.disabled = true;')
    text=once(text,"      const { response, data } = await callAuthenticated(session, { operation: 'new_thread' });\n      if (!response.ok", "      const { response, data } = await callAuthenticated(session, { operation: 'new_thread' });\n      if (!(await sameAccount(session,epoch))) return;\n      if (!response.ok")
    text=once(text,'      saveThreadId(data.thread_id);\n      state.history = [];','      saveThreadId(data.thread_id);\n      renderProjectMeta(data);\n      state.history = [];')
    text=once(text,"    } catch (_) {\n      addMessage(log, 'assistant', 'Chưa tạo được cuộc trò chuyện mới. Vui lòng thử lại.');\n    } finally {\n      button.disabled = false;", "    } catch (_) {\n      if (epoch === state.accountEpoch) addMessage(log, 'assistant', 'Chưa tạo được cuộc trò chuyện mới. Vui lòng thử lại.');\n    } finally {\n      state.sending = false;\n      button.disabled = false;")
    text=once(text,'  async function ask(message, log, input, send, status) {\n    if (state.sending) return;','  async function ask(message, log, input, send, status) {\n    if (state.sending || state.hydrating) return;\n    const epoch = state.accountEpoch;')
    text=once(text,'      const account = await currentAccountTier();\n      const session = account.session;','      const account = await currentAccountTier();\n      if (epoch !== state.accountEpoch) return;\n      const session = account.session;')
    text=once(text,'      if (response.status === 401 && authenticated) {','      if (!(await sameAccount(session,epoch))) return;\n      if (response.status === 401 && authenticated) {')
    text=once(text,'      if (response.ok) {\n        state.history.push','      if (response.ok && !authenticated) {\n        state.history.push')
    text=once(text,'        if (authenticated) await renderThreads(session, state.ui.threadList, log);\n      }','      }\n      if (response.ok && authenticated) await renderThreads(session, state.ui.threadList, log);')
    text=once(text,'    } catch (error) {\n      window.StockRadarAnalytics?.aiFailed','    } catch (error) {\n      if (epoch !== state.accountEpoch) return;\n      window.StockRadarAnalytics?.aiFailed')
    text=once(text,'state.ui = { host, threadList, threadToggle, log, sideNewChat, newChat, projectResume };','state.ui = { host, threadList, threadToggle, log, sideNewChat, newChat, projectResume, continuity };')
    text=once(text,"      if (!message) return;\n      addMessage(log, 'user', message);","      if (!message || state.sending || state.hydrating) return;\n      addMessage(log, 'user', message);")
    text=once(text,"        const {response,data} = await callAuthenticated(current.session,{operation:'resume_project'});\n        if (!response.ok || !data.thread_id) throw new Error('PROJECT_NOT_LINKED');\n        await hydrateHistory(current.session,log,data.thread_id);\n        await renderThreads(current.session,threadList,log);\n        closeThreadDrawer();", "        if (await resumeProject(current.session,log)) {\n          await renderThreads(current.session,threadList,log);\n          closeThreadDrawer();\n        }")
    text=once(text,'      if (authenticated) await hydrateHistory(account.session, log);','      if (authenticated) await hydrateHistory(account.session, log, state.threadId, true);')
    text=once(text,'      client?.auth?.onAuthStateChange?.(() => {','      client?.auth?.onAuthStateChange?.((_event,session) => {\n        if (!bindAccount(session)) return;')
    text=once(text,'            if (nextAuth) await hydrateHistory(next.session, log);','            if (nextAuth) await hydrateHistory(next.session, log, state.threadId, true);')
    return text

if __name__=='__main__':
    path=ROOT/'website/assets/ai-center.js'
    before=path.read_text(encoding='utf-8')
    after=apply(before)
    if after!=before: path.write_text(after,encoding='utf-8')
    print('Account-scoped conversation continuity source prepared; verification required before merge.')
