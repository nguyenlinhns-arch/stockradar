import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const source=fs.readFileSync(new URL('../supabase/functions/stockradar-native-probe/widget.ts',import.meta.url),'utf8');
const box={};vm.runInNewContext(source.replace('export default','globalThis.html ='),box);
const script=box.html.match(/<script>([\s\S]*?)<\/script>/)[1];
const flush=async()=>{for(let i=0;i<24;i++)await Promise.resolve();};
function harness(options={}){
 let now=0,seq=0,fetches=0;const timers=new Map(),events=new Map(),docEvents=new Map(),sent=[],native=[],stored=[];
 let signal=options.signal??{available:true,pending:false,signal_version:'PENDING_BOOL_V1'};
 const ids=['run','check','stop','status','preview'];const elements=Object.fromEntries(ids.map(id=>[id,{disabled:['run','check','stop'].includes(id),textContent:'',listeners:{},addEventListener(n,fn){this.listeners[n]=fn;}}]));
 const parent={postMessage(m){if(m.method==='ui/notifications/initialized')return;
  if(m.method==='ui/message'){sent.push(m);if(options.message==='timeout')return;}
  if(m.method==='ui/initialize'&&options.init==='timeout')return;
  const err=m.method==='ui/message'&&options.message==='notfound'?{code:-32601}:m.method==='ui/message'&&options.message==='reject'?{code:-32000}:null;
  queueMicrotask(()=>events.get('message')?.({source:parent,data:{jsonrpc:'2.0',id:m.id,...(err?{error:err}:{result:{}})}}));
 }};
 const context={console,AbortController,Map,Promise,JSON,Date,setTimeout(fn,ms){const id=++seq;timers.set(id,{fn,at:now+ms});return id;},clearTimeout(id){timers.delete(id);},parent,
  document:{hidden:false,getElementById:id=>elements[id],addEventListener:(k,fn)=>docEvents.set(k,fn)},
  addEventListener:(k,fn)=>events.set(k,fn),
  fetch:async(url,init)=>{fetches++;assert.ok(url.endsWith('/signal'));assert.equal(init.credentials,'omit');if(options.fetch)return options.fetch(url,init);if(options.http)return {ok:false,status:options.http};return {ok:true,json:async()=>signal};}
 };
 context.window=context;context.openai={widgetState:options.saved,setWidgetState:s=>stored.push(s)};
 if(options.native)context.openai.sendFollowUpMessage=async data=>{native.push(data);if(options.native==='reject')throw Error('denied');if(options.native==='timeout')return new Promise(()=>{});return {};};
 vm.runInNewContext(script,context);
 return {elements,sent,native,stored,context,events,get fetches(){return fetches;},setSignal(s){signal=s;},async click(id){if(!elements[id].disabled)elements[id].listeners.click();await flush();},async advance(ms){const end=now+ms;let loops=0;await flush();while(true){const hit=[...timers].filter(([,t])=>t.at<=end).sort((a,b)=>a[1].at-b[1].at)[0];if(!hit)break;assert.ok(++loops<1000);now=hit[1].at;timers.delete(hit[0]);hit[1].fn();await flush();}now=end;await flush();},async hidden(value){context.document.hidden=value;docEvents.get('visibilitychange')?.();await flush();},async pagehide(){events.get('pagehide')?.({});await flush();},async pageshow(){events.get('pageshow')?.({persisted:true});await flush();}};
}
const yes={available:true,pending:true,signal_version:'PENDING_BOOL_V1'};
test('opening a card does not poll or send before explicit activation',async()=>{const h=harness();await flush();assert.equal(h.fetches,0);assert.equal(h.sent.length,0);assert.equal(h.elements.run.disabled,false);});
test('valid empty queue does not send',async()=>{const h=harness();await flush();await h.click('run');await h.advance(20000);assert.equal(h.sent.length,0);assert.match(h.elements.status.textContent,/chưa có câu WEBSITE/);});
test('steady pending signal sends once, not every 45 seconds',async()=>{const h=harness({signal:yes});await flush();await h.click('run');await h.advance(180000);assert.equal(h.sent.length,1);assert.match(h.elements.status.textContent,/không gửi lặp/);});
test('observed clear signal rearms the next pending signal',async()=>{const h=harness({signal:yes});await flush();await h.click('run');h.setSignal({...yes,pending:false});await h.advance(5000);h.setSignal(yes);await h.advance(5000);assert.equal(h.sent.length,2);});
test('unavailable signal is not presented as an empty queue',async()=>{const h=harness({signal:{...yes,available:false,pending:false}});await flush();await h.click('run');assert.equal(h.sent.length,0);assert.match(h.elements.status.textContent,/Chưa đọc được tín hiệu/);});
test('malformed signal cannot generate a message',async()=>{const h=harness({signal:{pending:true,available:true}});await flush();await h.click('run');assert.equal(h.sent.length,0);assert.match(h.elements.status.textContent,/Chưa đọc được/);});
test('HTTP failure only retries signal reading',async()=>{const h=harness({http:503});await flush();await h.click('run');await h.advance(30000);assert.equal(h.sent.length,0);assert.ok(h.fetches>=3);});
test('manual native check can verify the host even when queue is empty',async()=>{const h=harness();await flush();await h.click('check');assert.equal(h.sent.length,1);assert.equal(h.fetches,0);assert.match(h.elements.status.textContent,/chưa xác minh/);assert.ok(h.sent[0].params.content[0].text.includes('\n'));assert.ok(!h.sent[0].params.content[0].text.includes('Có ít nhất'));});
test('ambiguous host timeout pauses instead of automatic resend',async()=>{const h=harness({signal:yes,message:'timeout',native:true});await flush();await h.click('run');await h.advance(120000);assert.equal(h.sent.length,1);assert.equal(h.native.length,0);assert.match(h.elements.status.textContent,/Đã dừng gửi tự động/);});
test('explicit method-not-found alone permits compatibility fallback',async()=>{const h=harness({signal:yes,message:'notfound',native:true});await flush();await h.click('run');assert.equal(h.sent.length,1);assert.equal(h.native.length,1);assert.match(h.elements.status.textContent,/Host đã nhận/);});
test('host rejection is not retried on the compatibility API',async()=>{const h=harness({signal:yes,message:'reject',native:true});await flush();await h.click('run');await h.advance(60000);assert.equal(h.native.length,0);assert.equal(h.sent.length,1);});
test('stop while signal fetch is pending prevents a late send',async()=>{let resolve;const h=harness({fetch:()=>new Promise(r=>{resolve=r;})});await flush();await h.click('run');await h.click('stop');resolve({ok:true,json:async()=>yes});await flush();await h.advance(60000);assert.equal(h.sent.length,0);assert.equal(h.fetches,1);});
test('hidden card neither polls nor sends and resumes while visible',async()=>{const h=harness({signal:yes});await flush();await h.hidden(true);await h.click('run');await h.advance(20000);assert.equal(h.fetches,0);await h.hidden(false);await h.advance(100);assert.equal(h.sent.length,1);});
test('page close stops all future polling and dispatch',async()=>{const h=harness({signal:yes});await flush();await h.click('run');await h.pagehide();const n=h.fetches;await h.advance(60000);assert.equal(h.fetches,n);assert.equal(h.sent.length,1);});
test('bfcache restore requires new activation, preserves latch',async()=>{const h=harness({signal:yes});await flush();await h.click('run');await h.pagehide();await h.pageshow();await h.advance(10000);assert.equal(h.sent.length,1);assert.equal(h.elements.run.disabled,false);await h.click('run');assert.equal(h.sent.length,1);});
test('saved latch prevents duplicate dispatch when widget rerenders',async()=>{const h=harness({signal:yes,saved:{bridgeVersion:'0.4.0',latched:true}});await flush();await h.click('run');assert.equal(h.sent.length,0);});
test('unsupported MCP initialization can use detected OpenAI alias',async()=>{const h=harness({init:'timeout',native:true});await h.advance(12000);await h.click('check');assert.equal(h.native.length,1);assert.equal(h.sent.length,0);});
test('compatibility alias timeout is bounded and never auto-retried',async()=>{const h=harness({init:'timeout',native:'timeout',signal:yes});await h.advance(12000);await h.click('run');await h.advance(120000);assert.equal(h.native.length,1);assert.match(h.elements.status.textContent,/Đã dừng gửi tự động/);});
test('prompt contains no website data, owner credentials, or API inference calls',()=>{assert.ok(!script.includes('api.openai.com'));assert.ok(!script.includes('service_role'));assert.ok(script.includes('PROJECT_VERIFICATION'));assert.ok(script.includes('complete_stockradar_project_question'));assert.ok(script.includes('credentials:\'omit\''));});
