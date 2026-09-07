"""Keep the composer locked throughout initial private-context restoration."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MARK='// PROJECT_RESTORE_STARTUP_LOCK_V1'
p=ROOT/'website/assets/ai-center.js'
s=p.read_text(encoding='utf-8')
if MARK not in s:
 a=s.index('  async function restoreInitialConversation(session, log) {')
 z=s.index('  function threadLabel(row) {',a)
 replacement=r'''  async function restoreInitialConversation(session, log) {
    if (!session?.access_token) return false;
    const epoch = state.accountEpoch;
    const sequence = (state.restoreSequence || 0) + 1;
    state.restoreSequence = sequence;
    state.hydrating = true;
    const current = async () => state.restoreSequence === sequence && await sameAccount(session,epoch);
    const key = `${THREAD_KEY}:project-auto:${state.accountId}`;
    try {
      if (!(await current())) return false;
      try {
        const {response,data} = await callAuthenticated(session,{operation:'project_bridge'});
        if (!(await current())) return false;
        const bridge = data?.project_bridge;
        if (response.ok && bridge?.available === true && bridge.auto_resume === true && /^[A-Z0-9_.-]{1,100}$/i.test(String(bridge.version || ''))) {
          let seen = ''; try { seen = localStorage.getItem(key) || ''; } catch (_) {}
          if (seen !== bridge.version && await resumeProject(session,log)) {
            if (!(await current())) return false;
            try { localStorage.setItem(key,bridge.version); } catch (_) {}
            return true;
          }
        }
      } catch (_) {
        if (!(await current())) return false;
      }
      return await hydrateHistory(session,log,state.threadId,true);
    } finally {
      if (epoch === state.accountEpoch && sequence === state.restoreSequence) state.hydrating = false;
    }
  }

'''
 s=MARK+'\n'+s[:a]+replacement+s[z:]
 p.write_text(s,encoding='utf-8')
p=ROOT/'engine/tests/project_chat_continuity.test.mjs'
s=p.read_text(encoding='utf-8')
if MARK not in s:
 s+=r'''
// PROJECT_RESTORE_STARTUP_LOCK_V1
test('initial metadata restoration blocks submitting into the wrong thread',async()=>{
 const h=harness(),d=deferred();h.setReply(body=>body.operation==='project_bridge'?d.promise:Promise.resolve(response()));
 const work=h.api.restoreInitialConversation(A,h.log);await new Promise(r=>setImmediate(r));
 assert.equal(h.api.state.hydrating,true);await h.ask();assert.equal(h.calls.length,1);
 d.resolve({project_bridge:{available:true,auto_resume:true,thread_id:T,version:'AUTO_LOCK'}});
 assert.equal(await work,true);assert.equal(h.api.state.hydrating,false);assert.equal(h.api.state.threadId,T);
});
test('old account restoration does not release the new account startup lock',async()=>{
 const h=harness(),first=deferred(),second=deferred();let count=0;
 h.setReply(()=>++count===1?first.promise:second.promise);
 const old=h.api.restoreInitialConversation(A,h.log);await new Promise(r=>setImmediate(r));
 h.setSession(B);const next=h.api.restoreInitialConversation(B,h.log);await new Promise(r=>setImmediate(r));
 first.resolve({project_bridge:{available:false}});assert.equal(await old,false);assert.equal(h.api.state.hydrating,true);
 second.resolve(response(O,'ACCOUNT_B_ONLY',{project_bridge:{available:false}}));assert.equal(await next,true);
 assert.equal(h.api.state.hydrating,false);assert.ok(!textOf(h.log).includes('OWNER_A_PRIVATE'));
});
'''
 p.write_text(s,encoding='utf-8')
print('Initial restoration lock and race coverage prepared; no account or provider changes.')
