// WORKSPACE_EVIDENCE_READER_V2
(() => {
 'use strict';
 const DESTINATION='https://chatgpt.com/';
 const TIMEFRAMES={SHORT_TERM:'Ngắn hạn',MEDIUM_TERM:'3–6 tháng',LONG_TERM:'12 tháng',ACCUMULATION:'Tích sản'};
 let clientPromise,sequence=0,activeUser=null,authGeneration=0,observedClient=null;
 function node(tag,cls,text=''){const e=document.createElement(tag);if(cls)e.className=cls;if(text)e.textContent=text;return e;}
 function buildPrompt(question,horizon){
  const q=String(question||'').trim().slice(0,2000);
  if(!q)throw new Error('EMPTY_QUESTION');
  return `Phân tích theo phương pháp StockRadar — chỉ cổ phiếu HOSE.\n\nYÊU CẦU: ${q}\nKHUNG THỜI GIAN: ${TIMEFRAMES[horizon]||TIMEFRAMES.SHORT_TERM}.\n\nDùng 4M/Payback → CANSLIM → định giá Bear/Base/Bull → SEPA/VCP/Stage → VPA/Pocket Pivot → quản trị rủi ro.\nKiểm tra nguồn, thời điểm dữ liệu và điều chỉnh quyền trước khi phân tích. Không lấy trí nhớ làm giá hiện tại. Không tự đặt điểm mua, stop, target, xác suất hoặc gọi kết quả là Top toàn HOSE khi thiếu dữ liệu/độ bao phủ.\nĐưa kết luận trước; phân biệt dữ liệu đã kiểm chứng, giả định và phần còn thiếu.\n\nLƯU Ý: Đây chỉ là gói câu hỏi, chưa kèm dữ liệu thị trường, không phải khuyến nghị. Trong Project StockRadar đã kết nối, hãy đọc dữ liệu được cấp quyền rồi phân tích. Chỉ lưu kết quả riêng về StockRadar khi tôi yêu cầu; không tự công khai hoặc gửi email.`;
 }

 function bindSession(session){
  const id=String(session?.user?.id||'');
  if(activeUser===null){activeUser=id;return;}
  if(activeUser===id)return;
  activeUser=id;authGeneration++;sequence++;
  document.querySelectorAll('.sr-cg-reports').forEach(e=>e.replaceChildren(node('p','sr-cg-note','Phiên đăng nhập đã thay đổi. Bấm Tải lại báo cáo để đọc dữ liệu của tài khoản hiện tại.')));
 }
 function observeClient(c){
  if(c&&observedClient!==c){observedClient=c;c.auth?.onAuthStateChange?.((_event,s)=>bindSession(s));}
  return c;
 }
 function timestampText(value){
  if(typeof value!=='string'||!value.trim())return 'Chưa xác định';
  const date=new Date(value);return Number.isFinite(date.getTime())?date.toLocaleString('vi-VN',{timeZone:'Asia/Ho_Chi_Minh'})+' (giờ Việt Nam)':'Chưa xác định';
 }
 function dateOnlyText(value){
  if(typeof value!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(value))return null;
  const date=new Date(value+'T00:00:00Z');
  if(!Number.isFinite(date.getTime())||date.toISOString().slice(0,10)!==value)return null;
  return value.slice(8,10)+'/'+value.slice(5,7)+'/'+value.slice(0,4)+' (nguồn chỉ xác định ngày)';
 }
 function reportDataLabel(r){
  if(r.data_as_of){const d=dateOnlyText(r.data_as_of);if(d)return d;const stamp=timestampText(r.data_as_of);if(stamp!=='Chưa xác định')return stamp;}
  for(const e of Array.isArray(r.evidence)?r.evidence:[]){const d=dateOnlyText(e?.as_of_date);if(d)return d;}
  return 'Chưa xác định — không suy diễn giá hiện tại';
 }
 function evidenceView(evidence){
  const items=Array.isArray(evidence)?evidence.slice(0,50):[];
  if(!items.length)return null;
  const detail=node('details','sr-cg-evidence');detail.append(node('summary','',`Nguồn và phép kiểm tra (${items.length})`));
  const fields={kind:'Loại bằng chứng',title:'Nội dung',as_of_date:'Ngày dữ liệu',snapshot_id:'Mã bản dữ liệu',context_grade:'Mức sử dụng',source:'Nguồn',source_function:'Hàm đọc dữ liệu',verification:'Trạng thái xác minh',field:'Chỉ tiêu',value:'Giá trị',formula:'Phép tính',note:'Ghi chú',repository:'Kho mã nguồn',commit:'Phiên bản mã nguồn',url:'Địa chỉ nguồn'};
  for(const [i,item]of items.entries()){
   const block=node('section','sr-cg-source');block.append(node('h4','',`Bằng chứng ${i+1}`));
   if(!item||typeof item!=='object'||Array.isArray(item)){block.append(node('p','sr-cg-note','Không có mô tả nguồn theo định dạng được hỗ trợ.'));detail.append(block);continue;}
   let count=0;
   for(const [key,label]of Object.entries(fields)){const value=item[key];if(!['string','number','boolean'].includes(typeof value))continue;
    let text=String(value).slice(0,1500);
    if(key==='url'){try{const u=new URL(text);if(u.protocol!=='https:'||u.username||u.password)continue;}catch(_){continue;}}
    // Text only: sources cannot load remote images, execute HTML, or run URL schemes.
    block.append(node('p','sr-cg-note',`${label}: ${text}`));count++;
   }
   if(!count)block.append(node('p','sr-cg-note','Bằng chứng kỹ thuật đã được lưu; không có trường mô tả để hiển thị.'));
   detail.append(block);
  }
  return detail;
 }
 function reportView(r){
  const article=node('article','sr-cg-report');article.dataset.reportId=String(r.id||'');
  article.append(node('h3','',String(r.title||'Báo cáo riêng')),node('small','',`Bản nháp riêng · Đã lưu: ${timestampText(r.created_at)} · ${r.source==='IMPLEMENTATION_NOTE'?'Ghi nhận triển khai':'Được lưu từ Project ChatGPT'}`));
  if(r.ticker)article.append(node('small','',`${r.ticker} · ${TIMEFRAMES[r.horizon]||'Khung thời gian chưa xác định'} · Dữ liệu đến: ${reportDataLabel(r)}`));
  const detail=node('details');detail.append(node('summary','','Đọc báo cáo'),node('pre','',String(r.body||'')));article.append(detail);
  const evidence=evidenceView(r.evidence);if(evidence)article.append(evidence);
  return article;
 }

 async function getClient(){
  if(clientPromise)return clientPromise;
  clientPromise=(async()=>{
   const cfg=window.STOCKRADAR_AUTH_CONFIG||{};
   if(!cfg.configured||!cfg.supabaseUrl||!cfg.supabasePublishableKey)return null;
   if(window.StockRadarAuthClient)return observeClient(window.StockRadarAuthClient);
   if(!window.supabase?.createClient)await new Promise((resolve,reject)=>{const s=node('script');s.src='https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.95.0';s.onload=resolve;s.onerror=()=>reject(new Error('AUTH_LIBRARY_UNAVAILABLE'));document.head.append(s);});
   const client=window.StockRadarAuthClient||window.supabase.createClient(cfg.supabaseUrl,cfg.supabasePublishableKey,{auth:{persistSession:true,autoRefreshToken:true,detectSessionInUrl:true,storageKey:'stockradar-auth'}});
   window.StockRadarAuthClient=client;return observeClient(client);
  })();
  return clientPromise;
 }
 async function currentSession(){const c=await getClient();if(!c)return null;const {data,error}=await c.auth.getSession();if(error)throw error;return data?.session||null;}
 async function sameUser(id,seq,generation){const s=await currentSession();return seq===sequence&&generation===authGeneration&&activeUser===id&&s?.user?.id===id;}
 async function showReports(target){
  const seq=++sequence,startGeneration=authGeneration;target.replaceChildren(node('p','sr-cg-status','Đang tải báo cáo riêng…'));
  try{
   const c=await getClient(),session=await currentSession();
   if(seq!==sequence||startGeneration!==authGeneration)return;bindSession(session);if(seq!==sequence)return;const generation=authGeneration;
   if(!session?.user?.id){target.replaceChildren(node('p','sr-cg-note','Đăng nhập StockRadar để xem báo cáo đã lưu riêng theo tài khoản.'));const a=node('a','sr-cg-link','Đăng nhập StockRadar');a.href=new URL('dang-nhap/',document.baseURI).toString();target.append(a);return;}
   const id=session.user.id;
   const {data,error}=await c.from('stockradar_workspace_reports').select('id,title,ticker,horizon,body,evidence,data_as_of,status,source,created_at').eq('user_id',id).eq('status','DRAFT').order('created_at',{ascending:false}).limit(30);
   if(!(await sameUser(id,seq,generation)))return;
   if(error)throw new Error('REPORT_READ_FAILED');
   target.replaceChildren();
   if(!data?.length){target.append(node('p','sr-cg-note','Chưa có báo cáo được lưu từ Project ChatGPT. Bản phân tích mới chỉ xuất hiện tại đây sau khi bạn yêu cầu lưu.'));return;}
   target.append(node("p","sr-cg-note",`Đã đọc ${data.length} báo cáo riêng từ máy chủ. Thời điểm lưu không thay thế ngày dữ liệu.`));
   for(const r of data)target.append(reportView(r));
  }catch(_){if(seq===sequence)target.replaceChildren(node('p','sr-cg-note','Chưa tải được báo cáo. Nội dung riêng không được hiển thị khi phiên đăng nhập hoặc kết nối chưa được xác minh.'));}
 }
 async function showLegacyHistory(target){
  const seq=++sequence,startGeneration=authGeneration;target.replaceChildren(node('p','sr-cg-status','Đang mở lịch sử cũ…'));
  try{
   const session=await currentSession();if(seq!==sequence||startGeneration!==authGeneration)return;bindSession(session);if(seq!==sequence)return;const generation=authGeneration;if(!session?.user?.id){target.replaceChildren(node('p','sr-cg-note','Cần đăng nhập để đọc lịch sử cũ.'));return;}
   const cfg=window.STOCKRADAR_AUTH_CONFIG;const r=await fetch(`${cfg.supabaseUrl.replace(/\/$/,'')}/functions/v1/stock-ai-chat`,{method:'POST',headers:{'Content-Type':'application/json',apikey:cfg.supabasePublishableKey,Authorization:`Bearer ${session.access_token}`},body:JSON.stringify({operation:'history'}),signal:AbortSignal.timeout(20000)});
   const data=await r.json();if(!(await sameUser(session.user.id,seq,generation)))return;if(!r.ok)throw new Error('HISTORY_FAILED');
   target.replaceChildren(node('p','sr-cg-note','Lịch sử lưu trước khi chuyển sang làm việc trong ChatGPT. Đây không phải phản hồi mới hoặc dữ liệu giá hiện tại.'));
   for(const m of data.messages||[]){const d=node('details');d.append(node('summary','',m.scope==='project_handoff'?'Bản ngữ cảnh đã chuyển':m.role==='user'?'Câu hỏi đã lưu':'Phản hồi đã lưu'),node('pre','',String(m.content||'')));target.append(d);}
  }catch(_){if(seq===sequence)target.replaceChildren(node('p','sr-cg-note','Chưa mở được lịch sử cũ. Không có nội dung riêng nào được chuyển sang tài khoản khác.'));}
 }
 function mount(){
  if(window.STOCKRADAR_EXECUTION_MODE!=='CHATGPT_WORKSPACE')return;
  for(const host of document.querySelectorAll('[data-stockradar-ai-center],[data-stockradar-chatgpt-reports]')){
   if(host.dataset.chatgptMounted==='true')continue;host.dataset.chatgptMounted='true';host.classList.add('sr-cg-workspace');
   const reportsOnly=host.hasAttribute('data-stockradar-chatgpt-reports');
   host.replaceChildren(node('span','sr-cg-eyebrow','CHATGPT × STOCKRADAR'),node('h2','',reportsOnly?'Báo cáo đã lưu của bạn':'Phân tích tại ChatGPT. Lưu báo cáo tại StockRadar.'));
   host.append(node('p','sr-cg-lead','ChatGPT là nơi phân tích. StockRadar lưu dữ liệu và kết quả được chọn. Khung này không gọi thêm OpenAI API và không dùng chung tài khoản ChatGPT của quản trị viên.'));
   const status=node('p','sr-cg-status');status.setAttribute('aria-live','polite');
   const target=node('div','sr-cg-reports');
   if(!reportsOnly){
    const form=node('form','sr-center-form');const label=node('label','','Bạn muốn phân tích điều gì?');const input=node('textarea');input.maxLength=2000;input.rows=3;input.placeholder='Ví dụ: Phân tích FPT trong 3–6 tháng và các rủi ro cần theo dõi';input.setAttribute('aria-label','Yêu cầu phân tích trong ChatGPT');label.append(input);
    const select=node('select');select.setAttribute('aria-label','Khung thời gian');for(const [value,text]of Object.entries(TIMEFRAMES)){const o=node('option','',text);o.value=value;select.append(o);}
    const button=node('button','sr-cg-button sr-center-send','Chuẩn bị câu hỏi');button.type='submit';const actions=node('div','sr-cg-actions');actions.append(select,button);form.append(label,actions);host.append(form);
    const log=node('div','sr-center-log'),packet=node('section','sr-cg-packet');packet.hidden=true;const previewLabel=node('label','','Nội dung sẽ dùng trong ChatGPT');const preview=node('textarea');preview.rows=9;preview.readOnly=true;preview.setAttribute('aria-label','Gói câu hỏi ChatGPT');previewLabel.append(preview);
    const copy=node('button','sr-cg-button','Sao chép yêu cầu');copy.type='button';const open=node('a','sr-cg-link','Mở ChatGPT');open.href=DESTINATION;open.target='_blank';open.rel='noopener noreferrer';open.referrerPolicy='no-referrer';const packetActions=node('div','sr-cg-actions');packetActions.append(copy,open);packet.append(previewLabel,packetActions,node('p','sr-cg-note','Mở ChatGPT rồi dán yêu cầu. Nút này mở ChatGPT thông thường; chưa phải một GPT/app StockRadar công khai. Nó không tự mở Project riêng hoặc gửi nội dung qua URL.'));log.append(packet);host.append(log);
    form.addEventListener('submit',e=>{e.preventDefault();try{preview.value=buildPrompt(input.value,select.value);packet.hidden=false;status.textContent='Đã chuẩn bị câu hỏi trên trình duyệt. Chưa gửi cho mô hình và chưa phát sinh cuộc gọi API.';}catch(_){status.textContent='Hãy nhập câu hỏi trước khi tiếp tục.';}});
    copy.addEventListener('click',async()=>{try{await navigator.clipboard.writeText(preview.value);status.textContent='Đã sao chép. Nội dung chỉ chuyển sang ChatGPT khi bạn dán vào cuộc trò chuyện.';}catch(_){preview.focus();preview.select();status.textContent='Trình duyệt chưa cho phép sao chép tự động. Nội dung đã được chọn để sao chép.';}});
   }
   host.append(status);const links=node('div','sr-cg-actions');const reports=node('a','sr-cg-link',reportsOnly?'Về StockRadar AI':'Báo cáo đã lưu');reports.href=new URL(reportsOnly?'ai/':'bao-cao-chatgpt/',document.baseURI).toString();const history=node('button','sr-cg-link','Đọc lịch sử cũ');history.type='button';history.addEventListener('click',()=>showLegacyHistory(target));const refresh=node("button","sr-cg-link sr-cg-refresh","Tải lại báo cáo");refresh.type="button";refresh.addEventListener("click",()=>showReports(target));links.append(reports,refresh,history);host.append(links,target,node('p','sr-cg-note','Báo cáo mới mặc định là bản nháp riêng. Không tự công khai, gửi email hoặc phát lệnh. ChatGPT áp dụng giới hạn của tài khoản bạn; phí lưu trữ, dữ liệu và email của StockRadar là các dịch vụ riêng.'));
   if(reportsOnly)showReports(target);
  }
  getClient().catch(()=>{});
 }
 window.StockRadarWorkspace=Object.freeze({mount,buildPrompt});
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',mount,{once:true});else mount();
})();
