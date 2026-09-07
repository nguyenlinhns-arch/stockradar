// PROJECT_AUTORESUME_ROUTING_V1
import {test} from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import fs from 'node:fs';
const U='11111111-1111-4111-8111-111111111111',V='22222222-2222-4222-8222-222222222222',T='33333333-3333-4333-8333-333333333333',O='44444444-4444-4444-8444-444444444444';
const A={access_token:'fixture-a',user:{id:U}},B={access_token:'fixture-b',user:{id:V}};
const KEY='stockradar_ai_thread_id_v1';
function deferred(){let resolve;const promise=new Promise(r=>{resolve=r;});return {promise,resolve};}
class Element {
 constructor(){this.children=[];this.dataset={};this.textContent='';this.hidden=false;this.events={};this.classes=new Set();this.classList={add:s=>this.classes.add(s),remove:s=>this.classes.delete(s),toggle:s=>this.classes.has(s)?this.classes.delete(s):this.classes.add(s)};}
 append(...items){this.children.push(...items);for(const x of items)x.parentElement=this;}
 replaceChildren(...items){this.children=[];this.append(...items);}
 addEventListener(name,fn){this.events[name]=fn;}
 setAttribute(){} focus(){} remove(){}
 querySelector(){return null;}
 querySelectorAll(){return this.children;}
}
function textOf(el){return el.textContent+' '+el.children.map(textOf).join(' ');}
function harness(initial=A){
 let session=initial, reply=async body=>({thread_id:T,messages:[],project_bridge:{available:true,thread_id:T,version:'TEST_V1'}}),rpcReply=null;
 const storage=new Map(),calls=[],log=new Element(),list=new Element(),resume=new Element(),continuity=new Element();
 const client={auth:{getSession:async()=>({data:{session}})},rpc:async(name,args)=>name==='get_my_stockradar_access'?{data:{account_tier:'PAID',account_status:'ACTIVE'}}:rpcReply?await rpcReply():{data:[]}};
 const document={readyState:'loading',baseURI:'https://fixture.invalid/',addEventListener(){},createElement:()=>new Element(),querySelectorAll:()=>[],querySelector:()=>null};
 const sandbox={document,URL,AbortSignal,console,setTimeout,clearTimeout,matchMedia:()=>({matches:false}),localStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)},window:{STOCKRADAR_AUTH_CONFIG:{configured:true,supabaseUrl:'https://fixture.invalid',supabasePublishableKey:'fixture-only'},supabase:{createClient:()=>client},StockRadarAuthClient:client},fetch:async(url,args)=>{const body=JSON.parse(args.body);calls.push({url,body});const result=await reply(body);return {ok:!(result.httpStatus>=400),status:result.httpStatus||200,json:async()=>result};}};
 sandbox.globalThis=sandbox;
 let source=fs.readFileSync(new URL('../../website/assets/ai-center.js',import.meta.url),'utf8');
 source=source.replace("  if (document.readyState === 'loading')",'  globalThis.__test = {state,bindAccount,loadThreadId,saveThreadId,hydrateHistory,renderThreads,startNewThread,ask,resumeProject,restoreInitialConversation};\n  if (document.readyState === \'loading\')');
 vm.runInNewContext(source,sandbox);
 const api=sandbox.__test;api.state.ui={log,threadList:list,projectResume:resume,continuity};api.bindAccount(initial);
 return {api,storage,calls,log,list,resume,continuity,setSession(value){session=value;api.bindAccount(value);},setReply(fn){reply=fn;},setRpc(fn){rpcReply=fn;},async ask(message='Phân tích FPT'){return api.ask(message,log,new Element(),new Element(),new Element());}};
}
function response(thread=T,content='OWNER_A_PRIVATE',meta={}){return {status:'READY',thread_id:thread,messages:[{role:'user',content,scope:'project_handoff'}],project_bridge:{available:true,thread_id:thread,version:'TEST_V1'},...meta};}

test('thread pointers are scoped to account, while old unowned pointer is ignored',()=>{
 const h=harness();h.storage.set(KEY,O);h.api.saveThreadId(T);assert.equal(h.storage.get(`${KEY}:${U}`),T);assert.equal(h.api.loadThreadId(V),'');h.setSession(B);assert.equal(h.api.state.threadId,'');h.api.saveThreadId(O);h.setSession(A);assert.equal(h.api.state.threadId,T);assert.equal(h.storage.get(`${KEY}:${V}`),O);assert.equal(h.storage.has(KEY),false);
});
test('logout clears rendered private history, Guest buffer, selected id and resume control immediately',()=>{
 const h=harness();h.log.append(Object.assign(new Element(),{textContent:'PRIVATE_BEFORE_LOGOUT'}));h.api.state.history=[{content:'PRIVATE'}];h.api.saveThreadId(T);h.resume.hidden=false;h.setSession(null);assert.ok(!textOf(h.log).includes('PRIVATE'));assert.equal(h.api.state.history.length,0);assert.equal(h.api.state.threadId,'');assert.equal(h.resume.hidden,true);
});
test('successful restore labels the reviewed handoff and keeps signed-in content out of Guest history',async()=>{
 const h=harness();h.setReply(async()=>response());assert.equal(await h.api.hydrateHistory(A,h.log,T),true);assert.match(textOf(h.log),/OWNER_A_PRIVATE/);assert.match(textOf(h.log),/không phải tin nhắn nguyên văn/);assert.equal(h.api.state.history.length,0);assert.equal(h.continuity.textContent,'Hội thoại dự án đã mở');assert.equal(h.resume.hidden,false);assert.ok([...h.storage.values()].every(x=>!x.includes('OWNER_A_PRIVATE')));
});
test('late private history cannot render after a different account signs in',async()=>{
 const h=harness(),d=deferred();h.setReply(()=>d.promise);const work=h.api.hydrateHistory(A,h.log,T);await new Promise(r=>setImmediate(r));h.setSession(B);d.resolve(response());assert.equal(await work,false);assert.ok(!textOf(h.log).includes('OWNER_A_PRIVATE'));assert.equal(h.api.state.threadId,'');
});
test('sign out and back in as the same user invalidates a previous-session history response',async()=>{
 const h=harness(),d=deferred();h.setReply(()=>d.promise);const work=h.api.hydrateHistory(A,h.log,T);await new Promise(r=>setImmediate(r));h.setSession(null);h.setSession(A);d.resolve(response());assert.equal(await work,false);assert.ok(!textOf(h.log).includes('OWNER_A_PRIVATE'));
});
test('newest history request wins if responses arrive out of order',async()=>{
 const h=harness(),d=deferred();h.setReply(body=>body.thread_id===T?d.promise:Promise.resolve(response(O,'LATEST_THREAD')));const older=h.api.hydrateHistory(A,h.log,T);await new Promise(r=>setImmediate(r));assert.equal(await h.api.hydrateHistory(A,h.log,O),true);d.resolve(response());assert.equal(await older,false);assert.equal(h.api.state.threadId,O);assert.match(textOf(h.log),/LATEST_THREAD/);assert.ok(!textOf(h.log).includes('OWNER_A_PRIVATE'));
});
test('implicit startup can recover a removed pointer once without an inference request',async()=>{
 const h=harness();h.api.saveThreadId(O);h.setReply(async body=>body.thread_id?{httpStatus:404,reason:'THREAD_NOT_FOUND'}:response());assert.equal(await h.api.hydrateHistory(A,h.log,O,true),true);assert.equal(h.api.state.threadId,T);assert.deepEqual(h.calls.map(c=>c.body.operation),['history','history']);assert.equal(h.calls[1].body.thread_id,null);
});
test('explicit sidebar selection failure does not silently select another conversation',async()=>{
 const h=harness();h.api.saveThreadId(T);h.setReply(async()=>({httpStatus:404,reason:'THREAD_NOT_FOUND'}));assert.equal(await h.api.hydrateHistory(A,h.log,O),false);assert.equal(h.calls.length,1);assert.equal(h.api.state.threadId,T);
});
test('old account thread list cannot render after account transition',async()=>{
 const h=harness(),d=deferred();h.setRpc(()=>d.promise);const work=h.api.renderThreads(A,h.list,h.log);await new Promise(r=>setImmediate(r));h.setSession(B);d.resolve({data:[{thread_id:T,title:'PRIVATE_THREAD_TITLE'}]});await work;assert.ok(!textOf(h.list).includes('PRIVATE_THREAD_TITLE'));
});
test('in-flight AI answer cannot render or persist a pointer after logout',async()=>{
 const h=harness(),d=deferred();h.setReply(()=>d.promise);const work=h.ask();await new Promise(r=>setImmediate(r));assert.equal(h.calls.length,1);h.setSession(null);d.resolve({status:'READY',thread_id:T,answer:'PRIVATE_MODEL_RESPONSE'});await work;assert.ok(!textOf(h.log).includes('PRIVATE_MODEL_RESPONSE'));assert.equal(h.api.state.threadId,'');assert.equal(h.api.state.history.length,0);
});
test('Guest request never receives earlier authenticated conversation content',async()=>{
 const h=harness();h.setReply(async()=>response());await h.api.hydrateHistory(A,h.log,T);h.setSession(null);h.setReply(async()=>({status:'READY_FALLBACK',answer:'Guest public answer'}));await h.ask();const request=h.calls.at(-1);assert.match(request.url,/stock-ai-guest$/);assert.equal(request.body.history.length,0);assert.ok(!JSON.stringify(request.body).includes('OWNER_A_PRIVATE'));
});
test('authenticated answer is kept server-side, never appended to Guest buffer',async()=>{
 const h=harness();h.setReply(async()=>({status:'READY_FALLBACK',thread_id:T,answer:'PRIVATE_SIGNED_IN_REPLY'}));await h.ask();assert.match(textOf(h.log),/PRIVATE_SIGNED_IN_REPLY/);assert.equal(h.api.state.history.length,0);
});
test('new-thread response from a prior account cannot overwrite another account selection',async()=>{
 const h=harness(),d=deferred();h.setReply(()=>d.promise);const work=h.api.startNewThread(A,h.log,new Element());await new Promise(r=>setImmediate(r));h.setSession(B);d.resolve(response());await work;assert.equal(h.api.state.threadId,'');assert.equal(h.storage.has(`${KEY}:${V}`),false);
});
test('project resume is metadata/history only and cannot cross accounts',async()=>{
 const h=harness();h.setReply(async()=>response());assert.equal(await h.api.resumeProject(A,h.log),true);assert.deepEqual(h.calls.map(c=>c.body.operation),['resume_project','history']);const d=deferred();h.setReply(()=>d.promise);const work=h.api.resumeProject(A,h.log);await new Promise(r=>setImmediate(r));h.setSession(B);d.resolve(response());assert.equal(await work,false);assert.ok(!textOf(h.log).includes('OWNER_A_PRIVATE'));
});
test('token refresh for the same account does not erase draft or reload conversation',()=>{
 const h=harness();h.api.state.history=[{content:'guest-only-fixture'}];h.api.saveThreadId(T);const epoch=h.api.state.accountEpoch;assert.equal(h.api.bindAccount({...A,access_token:'refreshed-fixture'}),false);assert.equal(h.api.state.accountEpoch,epoch);assert.equal(h.api.state.threadId,T);
});


test('opted-in project auto-opens once per version and later preserves a manual thread selection',async()=>{
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
