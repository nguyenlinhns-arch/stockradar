(() => {
  'use strict';
  const number = value => value == null || !['number','string'].includes(typeof value) || String(value).trim() === '' ? null : Number.isFinite(Number(value)) ? Number(value) : null;
  function state(row) {
    if (!row.fresh) return 'Dữ liệu cũ';
    if (row.new_buy_allowed === true) return 'Đã xác nhận mua';
    if (!row.research_ready) return row.initial_setup ? 'Dấu hiệu · thiếu dữ liệu' : 'Chưa đủ dữ liệu';
    return row.initial_setup ? 'Có dấu hiệu ban đầu' : 'Theo dõi';
  }
  function selectRows(items, options = {}) {
    const {search = '', sector = '', filter = 'ready', sort = 'score'} = options;
    const matches = items.filter(r => (!search || r.ticker.includes(search.trim().toUpperCase())) && (!sector || r.sector === sector)
      && (filter === 'all' || filter === 'ready' && r.research_ready && r.fresh || filter === 'initial' && r.initial_setup
        || filter === 'buy' && r.new_buy_allowed === true && r.fresh || filter === 'missing' && (!r.research_ready || !r.fresh)));
    const value = r => !r.research_ready || !r.fresh ? null : number(sort === 'technical' || sort === 'flow' ? r.scores?.[sort] : sort === 'change' ? r.technical?.change_pct : r.score);
    return matches.sort((a,b) => {
      if (sort !== 'ticker') {
        const av=value(a),bv=value(b);
        if (av == null && bv != null) return 1;
        if (av != null && bv == null) return -1;
        if (av != null && bv != null && av !== bv) return bv-av;
      }
      return a.ticker.localeCompare(b.ticker);
    });
  }
  function validate(data) {
    if (data?.schema_version !== 'STOCKRADAR_RESEARCH_RADAR_V1' || data.mode !== 'RESEARCH_SCREEN' || !Array.isArray(data.items)
      || data.items.some(r => !/^[A-Z0-9]{3}$/.test(r.ticker) || typeof r.fresh !== 'boolean' || typeof r.research_ready !== 'boolean'
        || typeof r.new_buy_allowed !== 'boolean')) throw new Error('Invalid Radar response');
    return data;
  }
  if (typeof module !== 'undefined' && module.exports) module.exports = {number,state,selectRows,validate};
  if (typeof document === 'undefined') return;
  const root=document.querySelector('[data-live-research-radar]');
  if (!root) return;
  const $=selector=>root.querySelector(selector);
  const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fmt=(value,decimals=1)=>number(value)==null?'—':number(value).toLocaleString('vi-VN',{maximumFractionDigits:decimals});
  const money=value=>number(value)==null?'—':fmt(value,0)+'đ';
  const pct=value=>number(value)==null?'—':(number(value)>0?'+':'')+fmt(value,2)+'%';
  const date=value=>/^\d{4}-\d{2}-\d{2}$/.test(value||'')?value.split('-').reverse().join('/'):'—';
  const time=value=>value&&!isNaN(Date.parse(value))?new Intl.DateTimeFormat('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit',hour12:false}).format(new Date(value)):'—';
  let data=null,page=1,tab='ranking',client=null,loading=false,requestId=0,subscribed=false,reloadRequested=false;
  const pageSize=window.matchMedia('(max-width:600px)').matches?10:25;
  const options=()=>({search:$('[data-lr-search]').value,sector:$('[data-lr-sector]').value,filter:$('[data-lr-filter]').value,sort:$('[data-lr-sort]').value});
  function message(text,html='') { const target=$('[data-lr-message]');target.hidden=!text&&!html;target.innerHTML=esc(text)+html; }
  function clearData() { data=null;$('[data-lr-results]').innerHTML='';$('[data-lr-detail]').innerHTML='';$('[data-lr-workspace]').hidden=true;for(const name of ['total','ready','initial','buys'])$(`[data-lr-${name}]`).textContent='—'; }
  function resetView() { page=1;$('[data-lr-detail]').hidden=true;render(); }
  function render() {
    if (!data) return;
    const rows=selectRows(data.items,options());
    const totalPages=Math.max(1,Math.ceil(rows.length/pageSize));page=Math.min(page,totalPages);
    $('[data-lr-workspace]').hidden=false;
    $('[data-lr-pagination]').hidden=tab!=='ranking'||!rows.length;
    $('[data-lr-prev]').disabled=page===1;$('[data-lr-next]').disabled=page===totalPages;
    $('[data-lr-page]').textContent=`Trang ${page}/${totalPages} · ${rows.length} mã`;
    root.querySelectorAll('[data-lr-tab]').forEach(el=>el.setAttribute('aria-pressed',String(el.dataset.lrTab===tab)));
    if (!rows.length) { $('[data-lr-results]').innerHTML='<p class="lr-empty">Không có mã khớp bộ lọc. Chọn “Toàn HOSE” hoặc xóa lọc.</p>';return; }
    if (tab==='sectors') {
      const sectors=[...new Set(rows.map(r=>r.sector))].sort((a,b)=>a.localeCompare(b,'vi'));
      $('[data-lr-results]').innerHTML=`<div class="lr-sector-grid">${sectors.map(sector=>{const stocks=rows.filter(r=>r.sector===sector);return `<article class="lr-sector"><h2>${esc(sector)}</h2><p>${stocks.length} mã khớp bộ lọc</p>${stocks.slice(0,3).map(r=>`<div><button type="button" data-lr-ticker="${esc(r.ticker)}">${esc(r.ticker)}</button><span>${money(r.price)} · ${fmt(r.score)}/100</span></div>`).join('')}<button type="button" data-lr-open-sector="${esc(sector)}">Xem ngành →</button></article>`;}).join('')}</div>`;
      return;
    }
    const headings=['Mã / ngành','Giá đóng cửa','Thay đổi phiên','Điểm /100','Kỹ thuật /100','Dòng tiền /100','Trạng thái'];
    $('[data-lr-results]').innerHTML=`<div class="lr-table-wrap"><table class="lr-table"><caption>${rows.length} mã · bấm mã để xem chi tiết</caption><thead><tr>${headings.map(h=>`<th scope="col">${h}</th>`).join('')}</tr></thead><tbody>${rows.slice((page-1)*pageSize,page*pageSize).map(r=>{
      const cells=[`<button type="button" data-lr-ticker="${esc(r.ticker)}">${esc(r.ticker)}</button><small>${esc(r.sector)}</small>`,money(r.price),`<span class="${number(r.technical?.change_pct)>0?'lr-up':number(r.technical?.change_pct)<0?'lr-down':''}">${pct(r.technical?.change_pct)}</span>`,fmt(r.score),fmt(r.scores?.technical),fmt(r.scores?.flow),`<span class="lr-state">${state(r)}</span>`];
      return `<tr data-lr-row="${esc(r.ticker)}">${cells.map((c,i)=>`<td data-label="${headings[i]}">${c}</td>`).join('')}</tr>`;
    }).join('')}</tbody></table></div>`;
  }
  function detail(ticker) {
    const r=data?.items.find(r=>r.ticker===ticker);if(!r)return;
    const t=r.technical||{},b=r.business||{},s=r.scores||{};
    const p=number(r.price),pivot=number(t.pivot),volume=number(t.volume),average=number(t.volume20);
    const priceNote=p!=null&&pivot>0?`Giá ${money(p)} ${p<pivot?'thấp hơn':p>pivot?'cao hơn':'bằng'} mốc theo dõi ${money(pivot)}${p===pivot?'':` là ${money(Math.abs(p-pivot))} (${fmt(Math.abs(p-pivot)/pivot*100,2)}% tính theo mốc)`}.`:'Chưa có đủ giá và mốc theo dõi.';
    const volumeNote=volume!=null&&average>0?`${fmt(volume,0)} cổ phiếu trong phiên; bằng ${fmt(volume/average,2)} lần trung bình 20 phiên trước (${fmt(average,0)} cổ phiếu/phiên).`:'Chưa có đủ số liệu khối lượng để so sánh.';
    const target=$('[data-lr-detail]');target.hidden=false;
    target.innerHTML=`<header><div><h2>${esc(r.ticker)} · ${esc(r.sector)}</h2><p>${date(r.as_of_date)} · ${state(r)}</p></div><button type="button" data-lr-close>Đóng</button></header><div class="lr-layer-grid"><article><h3>Doanh nghiệp</h3><p>Điểm doanh nghiệp: ${fmt(s.business)}/100. Lợi nhuận trên vốn chủ sở hữu: ${fmt(b.roe_pct)}%.</p><p>Kỳ số liệu: ${esc(b.period||'chưa có')}. Điểm số chưa thay thế việc đánh giá ban lãnh đạo và lợi thế cạnh tranh.</p></article><article><h3>Tăng trưởng</h3><p>Lãi mỗi cổ phiếu so với cùng kỳ: ${pct(b.eps_growth_pct)}.</p><p>Lợi nhuận sau thuế: ${pct(b.profit_growth_pct)}. Lợi nhuận trước thuế: ${pct(b.pbt_growth_pct)}.</p><p>Dấu “—” là chưa có dữ liệu, không phải tăng trưởng bằng 0.</p></article><article><h3>Kỹ thuật ngắn hạn</h3><p>${priceNote}</p><p>Giá trung bình 20 / 50 / 200 phiên: ${money(t.ma20)} / ${money(t.ma50)} / ${money(t.ma200)}.</p></article><article><h3>Dòng tiền và khối lượng</h3><p>Điểm dòng tiền: ${fmt(s.flow)}/100.</p><p>${volumeNote}</p></article></div><p><a href="co-phieu/?ticker=${esc(r.ticker)}">Xem ${esc(r.ticker)}: ngắn hạn · 3–6 tháng · 12 tháng · tích sản →</a></p>`;
    target.scrollIntoView({block:'start',behavior:'smooth'});target.focus({preventScroll:true});
  }
  async function authClient() {
    const start=Date.now();
    while (!window.StockRadarAuthClient && Date.now()-start<10000) await new Promise(resolve=>setTimeout(resolve,100));
    if(!window.StockRadarAuthClient)throw new Error('Authentication unavailable');
    return window.StockRadarAuthClient;
  }
  async function load() {
    if(loading)return;loading=true;const id=++requestId;$('[data-lr-refresh]').disabled=true;
    try {
      client=await authClient();
      if (!subscribed) {subscribed=true;client.auth.onAuthStateChange(event=>{
        if(event==='SIGNED_OUT'){requestId++;clearData();message('Đã đăng xuất. Đăng nhập để xem Radar.');}
        if(['SIGNED_IN','SIGNED_OUT'].includes(event)){reloadRequested=true;if(!loading){reloadRequested=false;setTimeout(load,0);}}
      });}
      const {data:auth,error}=await client.auth.getSession();if(error)throw error;
      if(!auth?.session){clearData();message('Đăng nhập để xem Radar từ dữ liệu nghiên cứu.', '<div><a class="button button-primary" href="dang-nhap/">Đăng nhập</a> <a href="dang-ky/?plan=free">Tạo tài khoản miễn phí →</a></div>');$('[data-lr-date]').textContent='Dành cho tài khoản Free và Premium.';return;}
      const config=window.STOCKRADAR_AUTH_CONFIG;
      const response=await fetch(`${config.supabaseUrl}/rest/v1/rpc/get_stockradar_radar_v1`,{method:'POST',headers:{apikey:config.supabasePublishableKey,Authorization:`Bearer ${auth.session.access_token}`,'Content-Type':'application/json'},body:'{}',cache:'no-store',signal:AbortSignal.timeout(15000)});
      if(!response.ok)throw new Error(response.status===401||response.status===403?'AUTH':'LOAD');
      const result=validate(await response.json());if(id!==requestId)return;data=result;
      const c=data.coverage||{};for(const [name,key] of [['total','total'],['ready','research_ready'],['initial','initial_setups'],['buys','published_buys']])$(`[data-lr-${name}]`).textContent=fmt(c[key],0);
      $('[data-lr-date]').textContent=`Giá: ${date(data.snapshot?.as_of_date)} · Rà soát: ${time(data.snapshot?.evaluated_at)} · giờ VN`;
      const schedule=data.schedule||{};$('[data-lr-schedule]').textContent=`Lượt tiếp theo dự kiến: ${time(schedule.next_review_at)}. Lịch ngày làm việc, có thể thay đổi vào ngày nghỉ. Trang tự kiểm tra dữ liệu mới mỗi phút khi đang mở.`;
      const previous=$('[data-lr-sector]').value;const sectors=[...new Set(data.items.map(r=>r.sector))].sort((a,b)=>a.localeCompare(b,'vi'));
      $('[data-lr-sector]').innerHTML='<option value="">Tất cả ngành</option>'+sectors.map(s=>`<option value="${esc(s)}">${esc(s)}</option>`).join('');if(sectors.includes(previous))$('[data-lr-sector]').value=previous;
      message(data.items.some(r=>!r.fresh)?'Có dữ liệu cũ; các mã đó không được xếp hạng hoặc coi là điểm mua mới.':'');render();
    } catch(error) { if(id!==requestId)return;if(error.message==='AUTH')clearData();message(error.message==='AUTH'?'Phiên đăng nhập hoặc quyền tài khoản cần kiểm tra lại. Đăng nhập lại rồi chọn “Làm mới”.':data?'Chưa cập nhật được. Bảng vẫn giữ dữ liệu theo mốc thời gian đang ghi; chọn “Làm mới” để thử lại.':'Chưa tải được Radar. Chọn “Làm mới” để thử lại.'); }
    finally {loading=false;$('[data-lr-refresh]').disabled=false;if(reloadRequested){reloadRequested=false;setTimeout(load,0);}}
  }
  for(const selector of ['[data-lr-search]','[data-lr-sector]','[data-lr-filter]','[data-lr-sort]'])$(selector).addEventListener(selector==='[data-lr-search]'?'input':'change',resetView);
  $('[data-lr-reset]').addEventListener('click',()=>{$('[data-lr-search]').value='';$('[data-lr-sector]').value='';$('[data-lr-filter]').value='ready';$('[data-lr-sort]').value='score';resetView();});
  $('[data-lr-prev]').addEventListener('click',()=>{page--;render();});$('[data-lr-next]').addEventListener('click',()=>{page++;render();});$('[data-lr-refresh]').addEventListener('click',load);
  root.addEventListener('click',e=>{const ticker=e.target.closest('[data-lr-ticker]');if(ticker)detail(ticker.dataset.lrTicker);const view=e.target.closest('[data-lr-tab]');if(view){tab=view.dataset.lrTab;resetView();}const sector=e.target.closest('[data-lr-open-sector]');if(sector){$('[data-lr-sector]').value=sector.dataset.lrOpenSector;tab='ranking';resetView();}if(e.target.closest('[data-lr-close]'))$('[data-lr-detail]').hidden=true;});
  const start=()=>{load();setInterval(()=>{if(!document.hidden)load();},60000);};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
