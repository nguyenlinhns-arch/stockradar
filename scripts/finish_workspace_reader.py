"""Display stored evidence and protect report/history rendering across sessions.
No new provider, model call, database permissions, publication or email behavior.
"""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MARK='// WORKSPACE_EVIDENCE_READER_V2'
def once(s,old,new):
    if s.count(old)!=1: raise RuntimeError(f'Source drift: {s.count(old)} matches for {old[:100]!r}')
    return s.replace(old,new,1)
def apply(s):
    if MARK in s:return s
    s=MARK+'\n'+s
    s=once(s,"let clientPromise,sequence=0,activeUser='';","let clientPromise,sequence=0,activeUser=null,authGeneration=0,observedClient=null;")
    helpers=r'''
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
'''
    s=once(s,' async function getClient(){',helpers+'\n async function getClient(){')
    s=once(s,'if(window.StockRadarAuthClient)return window.StockRadarAuthClient;','if(window.StockRadarAuthClient)return observeClient(window.StockRadarAuthClient);')
    s=once(s,'window.StockRadarAuthClient=client;return client;','window.StockRadarAuthClient=client;return observeClient(client);')
    s=once(s,'async function sameUser(id,seq){const s=await currentSession();return seq===sequence&&s?.user?.id===id;}','async function sameUser(id,seq,generation){const s=await currentSession();return seq===sequence&&generation===authGeneration&&activeUser===id&&s?.user?.id===id;}')
    s=once(s,"const seq=++sequence;target.replaceChildren(node('p','sr-cg-status','Đang tải báo cáo riêng…'));","const seq=++sequence,startGeneration=authGeneration;target.replaceChildren(node('p','sr-cg-status','Đang tải báo cáo riêng…'));")
    s=once(s,'const c=await getClient(),session=await currentSession();','const c=await getClient(),session=await currentSession();\n   if(seq!==sequence||startGeneration!==authGeneration)return;bindSession(session);if(seq!==sequence)return;const generation=authGeneration;')
    s=once(s,'const id=session.user.id;activeUser=id;','const id=session.user.id;')
    s=once(s,'await sameUser(id,seq)','await sameUser(id,seq,generation)')
    a=s.index('   for(const r of data){');z=s.index('\n  }catch(_)',a)
    s=s[:a]+'   target.append(node("p","sr-cg-note",`Đã đọc ${data.length} báo cáo riêng từ máy chủ. Thời điểm lưu không thay thế ngày dữ liệu.`));\n   for(const r of data)target.append(reportView(r));'+s[z:]
    s=once(s,"const seq=++sequence;target.replaceChildren(node('p','sr-cg-status','Đang mở lịch sử cũ…'));","const seq=++sequence,startGeneration=authGeneration;target.replaceChildren(node('p','sr-cg-status','Đang mở lịch sử cũ…'));")
    s=once(s,'const session=await currentSession();if(!session?.user?.id){','const session=await currentSession();if(seq!==sequence||startGeneration!==authGeneration)return;bindSession(session);if(seq!==sequence)return;const generation=authGeneration;if(!session?.user?.id){')
    s=once(s,'await sameUser(session.user.id,seq)','await sameUser(session.user.id,seq,generation)')
    s=once(s,'links.append(reports,history);','const refresh=node("button","sr-cg-link sr-cg-refresh","Tải lại báo cáo");refresh.type="button";refresh.addEventListener("click",()=>showReports(target));links.append(reports,refresh,history);')
    s=once(s,"getClient().then(c=>c?.auth?.onAuthStateChange?.((_event,s)=>{const id=s?.user?.id||'';if(activeUser&&id!==activeUser){sequence++;document.querySelectorAll('.sr-cg-reports').forEach(e=>e.replaceChildren());}activeUser=id;})).catch(()=>{});","getClient().catch(()=>{});")
    return s
if __name__=='__main__':
    p=ROOT/'website/assets/chatgpt-workspace.js'
    before=p.read_text(encoding='utf-8');after=apply(before)
    if after!=before:p.write_text(after,encoding='utf-8')
    print('Evidence reader, data-date precision, refresh and session isolation updated.')
