(() => {
 'use strict';
 const DESTINATION='https://chatgpt.com/';
 const TIMEFRAMES={SHORT_TERM:'Ngắn hạn',MEDIUM_TERM:'3–6 tháng',LONG_TERM:'12 tháng',ACCUMULATION:'Tích sản'};
 let clientPromise,sequence=0,activeUser='';
 function node(tag,cls,text=''){const e=document.createElement(tag);if(cls)e.className=cls;if(text)e.textContent=text;return e;}
 function buildPrompt(question,horizon){
  const q=String(question||'').trim().slice(0,2000);
  if(!q)throw new Error('EMPTY_QUESTION');
  return `Phân tích theo phương pháp StockRadar — chỉ cổ phiếu HOSE.\n\nYÊU CẦU: ${q}\nKHUNG THỜI GIAN: ${TIMEFRAMES[horizon]||TIMEFRAMES.SHORT_TERM}.\n\nDùng 4M/Payback → CANSLIM → định giá Bear/Base/Bull → SEPA/VCP/Stage → VPA/Pocket Pivot → quản trị rủi ro.\nKiểm tra nguồn, thời điểm dữ liệu và điều chỉnh quyền trước khi phân tích. Không lấy trí nhớ làm giá hiện tại. Không tự đặt điểm mua, stop, target, xác suất hoặc gọi kết quả là Top toàn HOSE khi thiếu dữ liệu/độ bao phủ.\nĐưa kết luận trước; phân biệt dữ liệu đã kiểm chứng, giả định và phần còn thiếu.\n\nLƯU Ý: Đây chỉ là gói câu hỏi, chưa kèm dữ liệu thị trường, không phải khuyến nghị. Trong Project StockRadar đã kết nối, hãy đọc dữ liệu được cấp quyền rồi phân tích. Chỉ lưu kết quả riêng về StockRadar khi tôi yêu cầu; không tự công khai hoặc gửi email.`;
 }
 async function getClient(){
  if(clientPromise)return clientPromise;
  clientPromise=(async()=>{
   const cfg=window.STOCKRADAR_AUTH_CONFIG||{};
   if(!cfg.configured||!cfg.supabaseUrl||!cfg.supabasePublishableKey)return null;
   if(window.StockRadarAuthClient)return window.StockRadarAuthClient;
   if(!window.supabase?.createClient)await new Promise((resolve,reject)=>{const s=node('script');s.src='https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.95.0';s.onload=resolve;s.onerror=()=>reject(new Error('AUTH_LIBRARY_UNAVAILABLE'));document.head.append(s);});
   const client=window.StockRadarAuthClient||window.supabase.createClient(cfg.supabaseUrl,cfg.supabasePublishableKey,{auth:{persistSession:true,autoRefreshToken:true,detectSessionInUrl:true,storageKey:'stockradar-auth'}});
   window.StockRadarAuthClient=client;return client;
  })();
  return clientPromise;
 }
 async function currentSession(){const c=await getClient();if(!c)return null;const {data,error}=await c.auth.getSession();if(error)throw error;return data?.session||null;}
 async function sameUser(id,seq){const s=await currentSession();return seq===sequence&&s?.user?.id===id;}
 async function showReports(target){
  const seq=++sequence;target.replaceChildren(node('p','sr-cg-status','Đang tải báo cáo riêng…'));
  try{
   const c=await getClient(),session=await currentSession();
   if(!session?.user?.id){target.replaceChildren(node('p','sr-cg-note','Đăng nhập StockRadar để xem báo cáo đã lưu riêng theo tài khoản.'));const a=node('a','sr-cg-link','Đăng nhập StockRadar');a.href=new URL('dang-nhap/',document.baseURI).toString();target.append(a);return;}
   const id=session.user.id;activeUser=id;
   const {data,error}=await c.from('stockradar_workspace_reports').select('id,title,ticker,horizon,body,evidence,data_as_of,status,source,created_at').eq('user_id',id).eq('status','DRAFT').order('created_at',{ascending:false}).limit(30);
   if(!(await sameUser(id,seq)))return;
   if(error)throw new Error('REPORT_READ_FAILED');
   target.replaceChildren();
   if(!data?.length){target.append(node('p','sr-cg-note','Chưa có báo cáo được lưu từ Project ChatGPT. Bản phân tích mới chỉ xuất hiện tại đây sau khi bạn yêu cầu lưu.'));return;}
   for(const r of data){const article=node('article','sr-cg-report');article.dataset.reportId=r.id;article.append(node('h3','',r.title));const when=new Date(r.created_at).toLocaleString('vi-VN',{timeZone:'Asia/Ho_Chi_Minh'});article.append(node('small','',`Bản nháp riêng · ${when} · ${r.source==='IMPLEMENTATION_NOTE'?'Ghi nhận triển khai':'Được lưu từ Project ChatGPT'}`));if(r.ticker)article.append(node('small','',`${r.ticker} · ${TIMEFRAMES[r.horizon]||'Khung thời gian chưa xác định'} · Dữ liệu: ${r.data_as_of?new Date(r.data_as_of).toLocaleString('vi-VN',{timeZone:'Asia/Ho_Chi_Minh'}):'Chưa xác định — không suy diễn giá hiện tại'}`));const detail=node('details');detail.append(node('summary','','Đọc báo cáo'),node('pre','',String(r.body||'')));article.append(detail);if(r.evidence?.length)article.append(node('small','',`${r.evidence.length} nguồn/bằng chứng được lưu cùng báo cáo.`));target.append(article);}
  }catch(_){if(seq===sequence)target.replaceChildren(node('p','sr-cg-note','Chưa tải được báo cáo. Nội dung riêng không được hiển thị khi phiên đăng nhập hoặc kết nối chưa được xác minh.'));}
 }
 async function showLegacyHistory(target){
  const seq=++sequence;target.replaceChildren(node('p','sr-cg-status','Đang mở lịch sử cũ…'));
  try{
   const session=await currentSession();if(!session?.user?.id){target.replaceChildren(node('p','sr-cg-note','Cần đăng nhập để đọc lịch sử cũ.'));return;}
   const cfg=window.STOCKRADAR_AUTH_CONFIG;const r=await fetch(`${cfg.supabaseUrl.replace(/\/$/,'')}/functions/v1/stock-ai-chat`,{method:'POST',headers:{'Content-Type':'application/json',apikey:cfg.supabasePublishableKey,Authorization:`Bearer ${session.access_token}`},body:JSON.stringify({operation:'history'}),signal:AbortSignal.timeout(20000)});
   const data=await r.json();if(!(await sameUser(session.user.id,seq)))return;if(!r.ok)throw new Error('HISTORY_FAILED');
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
   host.append(status);const links=node('div','sr-cg-actions');const reports=node('a','sr-cg-link',reportsOnly?'Về StockRadar AI':'Báo cáo đã lưu');reports.href=new URL(reportsOnly?'ai/':'bao-cao-chatgpt/',document.baseURI).toString();const history=node('button','sr-cg-link','Đọc lịch sử cũ');history.type='button';history.addEventListener('click',()=>showLegacyHistory(target));links.append(reports,history);host.append(links,target,node('p','sr-cg-note','Báo cáo mới mặc định là bản nháp riêng. Không tự công khai, gửi email hoặc phát lệnh. ChatGPT áp dụng giới hạn của tài khoản bạn; phí lưu trữ, dữ liệu và email của StockRadar là các dịch vụ riêng.'));
   if(reportsOnly)showReports(target);
  }
  getClient().then(c=>c?.auth?.onAuthStateChange?.((_event,s)=>{const id=s?.user?.id||'';if(activeUser&&id!==activeUser){sequence++;document.querySelectorAll('.sr-cg-reports').forEach(e=>e.replaceChildren());}activeUser=id;})).catch(()=>{});
 }
 window.StockRadarWorkspace=Object.freeze({mount,buildPrompt});
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',mount,{once:true});else mount();
})();
