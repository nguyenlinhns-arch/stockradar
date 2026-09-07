// Owner-only question/reply channel. No ChatGPT session proxy or background model trigger.
(() => {
 'use strict';
 const STATES={WAITING:'Chờ dự án xử lý',PROCESSING:'Dự án đã nhận để xử lý',ANSWERED:'Đã có câu trả lời từ dự án',CANCELLED:'Đã hủy'};
 const HORIZONS={SHORT_TERM:'Ngắn hạn',MEDIUM_TERM:'3–6 tháng',LONG_TERM:'12 tháng',ACCUMULATION:'Tích sản'};
 const UUID=/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
 function createChannel({client,getSession,onState=()=>{},onRows=()=>{},uuid=()=>crypto.randomUUID()}){
  let user='',generation=0,sequence=0,available=false,sending=false,draft=null;
  function bind(session){const id=String(session?.user?.id||'');if(id===user)return false;user=id;generation++;sequence++;available=false;draft=null;sending=false;onRows([]);onState({available:false,authenticated:!!user,busy:false,reset:true});return true;}
  async function current(epoch,id){const s=await getSession();return epoch===generation&&user===id&&s?.user?.id===id;}
  async function connect(){
   const initial=generation;const s=await getSession();if(initial!==generation)return false;bind(s);const epoch=generation,id=user;
   if(!id)return false;
   const {data,error}=await client.rpc('get_my_stockradar_project_channel');
   if(!(await current(epoch,id)))return false;
   if(error){onState({available:false,authenticated:true,error:'CHANNEL_UNAVAILABLE'});return false;}
   available=data?.available===true;onState({available,authenticated:true,automatic:false});return available;
  }
  async function refresh(){
   const epoch=generation,id=user,seq=++sequence;if(!available||!id)return false;
   const {data,error}=await client.from('stockradar_project_questions').select('id,parent_id,question,horizon,status,origin,answer,evidence,answer_source,created_at,answered_at').eq('user_id',id).order('created_at',{ascending:false}).order('id',{ascending:false}).limit(30);
   if(seq!==sequence||!(await current(epoch,id)))return false;
   if(error){onState({available,authenticated:true,error:'READ_FAILED'});return false;}
   onRows(Array.isArray(data)?data:[]);onState({available,authenticated:true,refreshed:true});return true;
  }
  async function submit(question,horizon='SHORT_TERM',parentId=null){
   const msg=String(question||'').trim();if(!msg||msg.length>6000||!HORIZONS[horizon]||(parentId&&!UUID.test(parentId)))throw new Error('INVALID_QUESTION');
   if(!available||!user)throw new Error('CHANNEL_NOT_LINKED');if(sending)throw new Error('REQUEST_IN_PROGRESS');
   const epoch=generation,id=user;if(!(await current(epoch,id)))return null;
   const signature=JSON.stringify([msg,horizon,parentId]);if(!draft||draft.signature!==signature)draft={signature,key:uuid()};
   const key=draft.key;sending=true;onState({available,authenticated:true,busy:true});
   try{
    const {data,error}=await client.rpc('submit_my_stockradar_project_question',{p_question:msg,p_horizon:horizon,p_client_key:key,p_parent_id:parentId});
    if(!(await current(epoch,id)))return null;
    if(error)throw new Error(String(error.message||'SUBMIT_FAILED'));
    if(!UUID.test(String(data?.id||'')))throw new Error('INVALID_RECEIPT');
    draft=null;return data;
   }finally{if(epoch===generation){sending=false;onState({available,authenticated:true,busy:false});}}
  }
  async function cancel(id){
   if(!available||!UUID.test(String(id)))throw new Error('INVALID_QUESTION');const epoch=generation,owner=user;
   if(!(await current(epoch,owner)))return null;
   const {data,error}=await client.rpc('cancel_my_stockradar_project_question',{p_id:id});
   if(!(await current(epoch,owner)))return null;if(error)throw new Error('CANCEL_FAILED');return data;
  }
  return {bind,connect,refresh,submit,cancel};
 }
 function el(tag,cls,text=''){const n=document.createElement(tag);if(cls)n.className=cls;n.textContent=text;return n;}
 function stamp(value){const d=typeof value==='string'?new Date(value):null;return d&&Number.isFinite(d.getTime())?d.toLocaleString('vi-VN',{timeZone:'Asia/Ho_Chi_Minh'}):'Chưa xác định';}
 function questionView(row,follow,cancel){
  const card=el('article','sr-project-question');card.dataset.questionId=String(row.id||'');
  const status=STATES[row.status]||'Chưa xác định';card.append(el('strong','sr-project-state',status),el('small','',`${HORIZONS[row.horizon]||''} · Đã gửi: ${stamp(row.created_at)}`));
  if(row.origin==='PROJECT_VERIFICATION')card.append(el('small','','Kiểm chứng do dự án tạo · không phải tin nhắn nhập từ website'));
  card.append(el('p','sr-project-message',String(row.question||'')));
  if(row.status==='ANSWERED'&&typeof row.answer==='string'&&row.answer_source==='CHATGPT_PROJECT'){
   card.append(el('small','',`Trả lời tại dự án: ${stamp(row.answered_at)} · Không tự phát hành khuyến nghị`),el('div','sr-project-answer',row.answer));
   const b=el('button','sr-cg-link','Hỏi tiếp câu này');b.type='button';b.onclick=()=>follow(row);card.append(b);
  }else if(['WAITING','PROCESSING'].includes(row.status)){
   card.append(el('p','sr-cg-note','Câu hỏi đã được lưu riêng. Website chưa thể tự kích hoạt ChatGPT; dự án xử lý khi được gọi tại ChatGPT.'));
   const b=el('button','sr-cg-link','Hủy yêu cầu');b.type='button';b.onclick=()=>cancel(row);card.append(b);
  }
  return card;
 }
 async function getClient(){
  if(window.StockRadarAuthClient)return window.StockRadarAuthClient;
  const cfg=window.STOCKRADAR_AUTH_CONFIG||{};if(!cfg.configured)return null;
  if(!window.supabase?.createClient)await new Promise((resolve,reject)=>{const s=document.createElement('script');s.src='https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.95.0';s.onload=resolve;s.onerror=reject;document.head.append(s);});
  if(window.StockRadarAuthClient)return window.StockRadarAuthClient;
  window.StockRadarAuthClient=window.supabase.createClient(cfg.supabaseUrl,cfg.supabasePublishableKey,{auth:{persistSession:true,autoRefreshToken:true,detectSessionInUrl:true,storageKey:'stockradar-auth'}});return window.StockRadarAuthClient;
 }
 async function mount(){
  if(window.STOCKRADAR_EXECUTION_MODE!=='CHATGPT_WORKSPACE')return;
  const host=document.querySelector('[data-stockradar-ai-center]');if(!host||host.dataset.projectChannelMounted)return;host.dataset.projectChannelMounted='true';
  const box=el('section','sr-project-channel');box.hidden=true;
  box.append(el('h3','','Hỏi và nhận trả lời từ dự án'),el('p','sr-cg-note','Hai chiều dữ liệu, không cần sao chép câu hỏi hoặc câu trả lời. Chưa có kích hoạt mô hình tự động: sau khi gửi, yêu cầu xử lý hàng đợi tại Project ChatGPT; kết quả sẽ trở lại đây.'));
  const form=el('form','sr-project-form');const input=el('textarea');input.rows=3;input.maxLength=6000;input.setAttribute('aria-label','Câu hỏi gửi vào dự án');input.placeholder='Nhập câu hỏi cho dự án StockRadar';
  const select=el('select');select.setAttribute('aria-label','Khung phân tích');for(const [k,v]of Object.entries(HORIZONS)){const o=el('option','',v);o.value=k;select.append(o);}
  const submit=el('button','sr-cg-button','Gửi vào hàng đợi dự án');submit.type='submit';const refresh=el('button','sr-cg-link','Tải lại hội thoại');refresh.type='button';const controls=el('div','sr-cg-actions');controls.append(select,submit,refresh);form.append(input,controls);
  const context=el('p','sr-cg-note'),notice=el('p','sr-cg-status');notice.setAttribute('role','status');const list=el('div','sr-project-questions');box.append(form,context,notice,list);host.insertBefore(box,host.querySelector('.sr-center-form'));
  let parent=null,ready=false,busy=false,timer,disposed=false,channel;
  const oldForm=host.querySelector('.sr-center-form'),oldLog=host.querySelector('.sr-center-log');
  function schedule(){clearTimeout(timer);if(!disposed&&ready&&!document.hidden)timer=setTimeout(async()=>{try{await channel.refresh();}catch(_){notice.textContent='Chưa đọc được cập nhật từ máy chủ.';}schedule();},5000);}
  function state(s){
   ready=s.available===true;box.hidden=!ready;if(oldForm)oldForm.hidden=ready;if(oldLog)oldLog.hidden=ready;
   if(typeof s.busy==='boolean')busy=s.busy;submit.disabled=busy||!ready;
   if(s.reset||!s.authenticated){list.replaceChildren();input.value='';context.textContent='';parent=null;}
   if(s.error)notice.textContent='Chưa xác minh được kết nối dữ liệu. Không có câu trả lời mới được tạo.';
   schedule();
  }
  function render(rows){list.replaceChildren();if(!rows.length){list.append(el('p','sr-cg-note','Chưa có câu hỏi trong kênh này.'));return;}
   for(const r of rows.slice().reverse())list.append(questionView(r,row=>{parent=row.id;select.value=row.horizon;context.textContent='Câu tiếp theo sẽ tham chiếu câu trả lời đã chọn.';input.focus();},async row=>{try{await channel.cancel(row.id);await channel.refresh();}catch(_){notice.textContent='Chưa hủy được yêu cầu; hãy tải lại trạng thái trước khi thử lại.';}}));
  }
  try{
   const client=await getClient();if(!client)return;
   const getSession=async()=>{const {data,error}=await client.auth.getSession();if(error)throw error;return data?.session||null;};
   channel=createChannel({client,getSession,onState:state,onRows:render});
   client.auth.onAuthStateChange((_event,s)=>{if(channel.bind(s))setTimeout(async()=>{try{await channel.connect();await channel.refresh();schedule();}catch(_){state({available:false,authenticated:!!s,error:true});}},0);});
   await channel.connect();await channel.refresh();schedule();
   form.addEventListener('submit',async e=>{e.preventDefault();if(busy||!ready)return;try{const receipt=await channel.submit(input.value,select.value,parent);if(receipt){input.value='';parent=null;context.textContent='';notice.textContent='Đã lưu câu hỏi để dự án đọc. Chưa kích hoạt mô hình ChatGPT tự động.';await channel.refresh();}}catch(err){notice.textContent=/PROJECT_QUEUE_LIMIT/.test(String(err.message))?'Hàng đợi đang đầy hoặc gửi quá nhanh. Hãy xử lý/hủy yêu cầu cũ trước.':'Chưa xác nhận gửi thành công. Thử lại cùng nội dung sẽ không tạo yêu cầu trùng.';}});
   refresh.onclick=()=>channel.refresh().catch(()=>{notice.textContent='Chưa tải được hội thoại.';});
   document.addEventListener('visibilitychange',()=>{if(!document.hidden)channel.refresh().catch(()=>{});schedule();});
   window.addEventListener('pagehide',()=>{disposed=true;clearTimeout(timer);});
  }catch(_){box.hidden=true;}
 }
 window.StockRadarProjectChannel=Object.freeze({createChannel,questionView,mount});
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',mount,{once:true});else mount();
})();
