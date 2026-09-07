"""Source-anchored routing repair and opt-in, once-per-version project restoration."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MARK='// PROJECT_AUTORESUME_ROUTING_V1'

def once(s,old,new):
    if s.count(old)!=1: raise RuntimeError(f'Source drift ({s.count(old)} matches): {old[:100]}')
    return s.replace(old,new,1)

def section(s,start,end,new):
    if s.count(start)!=1 or s.count(end)!=1: raise RuntimeError('Function boundaries changed')
    a=s.index(start);z=s.index(end,a)
    return s[:a]+new+'\n\n'+s[z:]

canonical=(ROOT/'scripts/templates/stock_ticker_extractor.js').read_text().rstrip()
explicit=canonical.replace('function extractStockTickers(text)','function explicitTicker(text)').replace('return tickers;','return tickers[0] || "";')

RESTORE=r'''  async function restoreInitialConversation(session, log) {
    const epoch = state.accountEpoch;
    if (!session?.access_token || !(await sameAccount(session,epoch))) return false;
    const key = `${THREAD_KEY}:project-auto:${state.accountId}`;
    try {
      const {response,data} = await callAuthenticated(session,{operation:'project_bridge'});
      if (!(await sameAccount(session,epoch))) return false;
      const bridge = data?.project_bridge;
      if (response.ok && bridge?.available === true && bridge.auto_resume === true && /^[A-Z0-9_.-]{1,100}$/i.test(String(bridge.version || ''))) {
        let seen = ''; try { seen = localStorage.getItem(key) || ''; } catch (_) {}
        if (seen !== bridge.version && await resumeProject(session,log)) {
          if (!(await sameAccount(session,epoch))) return false;
          try { localStorage.setItem(key,bridge.version); } catch (_) {}
          return true;
        }
      }
    } catch (_) {
      if (!(await sameAccount(session,epoch))) return false;
    }
    return await hydrateHistory(session,log,state.threadId,true);
  }'''

HORIZON=r'''function explicitHorizon(text) {
  const q = String(text || '').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[đĐ]/g,'d').toLowerCase();
  if (/tich san|tich luy/.test(q)) return 'ACCUMULATION';
  if (/12\s*thang|dai han/.test(q)) return 'LONG_TERM';
  if (/3\s*[-–]\s*6\s*thang|trung han|6\s*thang/.test(q)) return 'MEDIUM_TERM';
  if (/ngan han|vai phien|vai tuan/.test(q)) return 'SHORT_TERM';
  return '';
}'''

def chat(s):
    s=section(s,'function explicitTicker(text: string) {','function portfolioIntent(text: string) {',explicit+'\n\n'+HORIZON)
    s=section(s,'function scanIntent(text: string) {','function methodologyIntent(text: string) {',r'''function scanIntent(text: string) {
  return /(\btop\b|quét|quet|lọc|loc|mã nào|ma nao|cổ phiếu nào|co phieu nao|ngành nào|nganh nao)/i.test(text);
}''')
    s=section(s,'function methodologyIntent(text: string) {','function horizon(value: unknown, fallback = "SHORT_TERM") {',r'''function methodologyIntent(text: string) {
  if (explicitTicker(text)) return false;
  if (/(liên thông|lien thong|ngữ cảnh|ngu canh|dự án|du an|chatgpt|cuộc trò chuyện|cuoc tro chuyen)/i.test(text)) return true;
  const method = /(4m|payback|canslim|sepa|vcp|vpa|pocket pivot|ichimoku|bollinger|stage\s*[1-4]|fair value|margin of safety|định giá|dinh gia|phương pháp|phuong phap|quản trị rủi ro|quan tri rui ro)/i.test(text);
  return method && (/(là gì|la gi|giải thích|giai thich|khái niệm|khai niem|hướng dẫn|huong dan|phương pháp|phuong phap)/i.test(text) || /^(4m|payback|canslim|sepa|vcp|vpa|pocket pivot|ichimoku|bollinger)\s*[?.!]*$/i.test(text.trim()));
}''')
    s=once(s,'const inputHorizon = horizon(body.horizon,','const inputHorizon = horizon(explicitHorizon(message) || body.horizon,')
    return s

def query(s):
    a=s.index('const STOP = new Set(');z=s.index('\nexport function parseResearchQuery',a)
    s=s[:a]+canonical+'\n'+s[z:]
    a=s.index('  // Accented Vietnamese words');z=s.index('  const filter =',a)
    s=s[:a]+'''  const explicit = extractStockTickers(message);
  const requested = String(requestedTicker || '').trim().toUpperCase();
  const tickers = explicit.length ? explicit : /^[A-Z0-9]{3}$/.test(requested) && /[A-Z]/.test(requested) ? [requested] : [];
  const scan = /\\b(top|quet|loc|ma nao|co phieu nao|nganh nao)\\b/.test(q) || (!tickers.length && /\\bnganh\\b/.test(q));
'''+s[z:]
    return s

def client(s):
    s=section(s,'  function explicitTicker(text) {','  function horizonFromText(text) {','\n'.join('  '+line if line else '' for line in explicit.splitlines()))
    s=once(s,'  function threadLabel(row) {',RESTORE+'\n\n  function threadLabel(row) {')
    s=once(s,'if (authenticated) await hydrateHistory(account.session, log, state.threadId, true);','if (authenticated) await restoreInitialConversation(account.session, log);')
    s=once(s,'if (nextAuth) await hydrateHistory(next.session, log, state.threadId, true);','if (nextAuth) await restoreInitialConversation(next.session, log);')
    return s

def context(s):
    s=once(s,'return {thread_id:b.thread_id, version:b.version,','return {auto_resume:b.auto_resume === true,thread_id:b.thread_id, version:b.version,')
    s=once(s,'return {available:true,thread_id:bridge.thread_id,','return {available:true,auto_resume:bridge.auto_resume === true,thread_id:bridge.thread_id,')
    return s

def client_tests(s):
    s=once(s,'ask,resumeProject};','ask,resumeProject,restoreInitialConversation};')
    s+='''\n\ntest('opted-in project auto-opens once per version and later preserves a manual thread selection',async()=>{
 const h=harness();h.setReply(async body=>body.operation==='project_bridge'?{project_bridge:{available:true,auto_resume:true,thread_id:T,version:'AUTO_V1'}}:response(body.thread_id || T));
 assert.equal(await h.api.restoreInitialConversation(A,h.log),true);
 assert.deepEqual(h.calls.map(c=>c.body.operation),['project_bridge','resume_project','history']);
 assert.equal(h.storage.get(`${KEY}:project-auto:${U}`),'AUTO_V1');
 h.api.saveThreadId(O);h.calls.length=0;
 assert.equal(await h.api.restoreInitialConversation(A,h.log),true);
 assert.deepEqual(h.calls.map(c=>c.body.operation),['project_bridge','history']);
 assert.equal(h.api.state.threadId,O);
});
test('ordinary users do not auto-resume and metadata errors still restore owned history',async()=>{
 for(const meta of [{available:false},{available:true,auto_resume:false,version:'AUTO_V1'}]){
  const h=harness();h.setReply(async body=>body.operation==='project_bridge'?{project_bridge:meta}:response());
  assert.equal(await h.api.restoreInitialConversation(A,h.log),true);
  assert.deepEqual(h.calls.map(c=>c.body.operation),['project_bridge','history']);
 }
 const h=harness();h.setReply(async body=>{if(body.operation==='project_bridge')throw new Error('offline');return response();});
 assert.equal(await h.api.restoreInitialConversation(A,h.log),true);
 assert.equal(h.calls.at(-1).body.operation,'history');
});
test('a late auto-resume metadata response cannot select or expose another account conversation',async()=>{
 const h=harness(),d=deferred();h.setReply(()=>d.promise);
 const work=h.api.restoreInitialConversation(A,h.log);await new Promise(r=>setImmediate(r));h.setSession(B);
 d.resolve({project_bridge:{available:true,auto_resume:true,thread_id:T,version:'AUTO_V1'}});
 assert.equal(await work,false);assert.equal(h.calls.length,1);assert.equal(h.api.state.threadId,'');
 assert.equal(h.storage.has(`${KEY}:project-auto:${V}`),false);
});
'''
    return s

def server_tests(s):
    s+='''\n\ntest('long Vietnamese lookup stays on the intended ticker through the real chat handler',async()=>{
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
'''
    return s

if __name__=='__main__':
    functions={
      'supabase/functions/stock-ai-chat/index.ts':chat,
      'supabase/functions/_shared/stockradar-query.ts':query,
      'website/assets/ai-center.js':client,
      'supabase/functions/_shared/stockradar-project-context.ts':context,
      'engine/tests/project_chat_continuity.test.mjs':client_tests,
      'engine/tests/private_project_chat.test.mjs':server_tests,
    }
    updates={}
    for path,fn in functions.items():
      source=(ROOT/path).read_text(encoding='utf-8')
      if MARK not in source: updates[path]=MARK+'\n'+fn(source)
    for path,source in updates.items(): (ROOT/path).write_text(source,encoding='utf-8')
    print(f'Prepared {len(updates)} source changes; no credential, entitlement or data-gate edits.')
