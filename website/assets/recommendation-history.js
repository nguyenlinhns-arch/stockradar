(() => {
  'use strict';
  const target = document.querySelector('[data-alert-history]');
  if (!target) return;
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const price = v => v == null ? '—' : Number(v).toLocaleString('vi-VN') + 'đ';
  const pct = v => v == null ? '—' : (v > 0 ? '+' : '') + Number(v).toLocaleString('vi-VN', {maximumFractionDigits:2}) + '%';
  const day = v => v ? v.slice(0,10).split('-').reverse().join('/') : '—';
  const time = v => new Intl.DateTimeFormat('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false}).format(new Date(v));
  const range = v => (v || []).map(price).join(' – ');
  const tone = v => v == null || v === 0 ? '' : v > 0 ? 'history-up' : 'history-down';
  const setup = {POCKET_PIVOT:'Mua sớm: khối lượng vượt phiên giảm',EARLY_BREAKOUT:'Giá gần vượt vùng cản',CONFIRMED_BREAKOUT:'Vượt cản, khối lượng xác nhận'};
  const exit = {NO_TECHNICAL_EXIT_SEEN:'Chưa thấy điều kiện thoát kỹ thuật',TECHNICAL_EXIT_SEEN:'Đã thấy điều kiện thoát kỹ thuật',UNRESOLVED_DATA:'Thiếu dữ liệu theo dõi'};
  async function get(name) {
    const response = await fetch(new URL('public/data/' + name,document.baseURI),{cache:'no-store',signal:AbortSignal.timeout(15000)});
    if (!response.ok) throw new Error('Không tải được lịch sử');
    return response.json();
  }
  function timeline(events) {
    return events.map(e => `<li><b>${esc(e.kind === 'BUY' ? 'Báo mua lần đầu' : e.kind === 'SELL' ? 'Báo bán' : 'Điều chỉnh khuyến nghị')}</b>
      <p>Phát hiện ${time(e.signal_at)} · Gửi ${time(e.sent_at)} · ${e.recipient_count} địa chỉ.</p>
      <p>Vùng mua lúc đó: ${range(e.buy_zone)} · Cắt lỗ: ${price(e.stop_loss)} · Mục tiêu gần trong thư: ${range(e.near_target)}.</p><p>${esc(e.note)}</p></li>`).join('');
  }
  function renderObserved(data) {
    if (data.schema_version !== 'STOCKRADAR_VERIFIED_HISTORY_V1') throw new Error('Sai định dạng lịch sử');
    const s = data.summary;
    target.innerHTML = `<header><span class="panel-label">ĐÃ ĐỐI CHIẾU EMAIL GỐC</span><h2>Những mã AI đã báo mua</h2>
      <p>${s.tickers} mã · ${s.alerts} lần gửi · ${s.without_sell_email} mã chưa tìm thấy email bán đến ${day(data.mail_search_through)}.</p></header>
      <div class="history-cards">${[...data.items].sort((a,b)=>Date.parse(b.first_sent_at)-Date.parse(a.first_sent_at)).map(r => `<article class="history-card" id="history-${esc(r.ticker)}"><header><h3>${esc(r.ticker)}</h3><span class="history-badge">${r.status==='NO_SELL_EMAIL_FOUND'?'Chưa có email bán':'Đã ghi nhận email bán'}</span></header>
        <p>Báo mua đầu tiên: <b>${time(r.first_sent_at)}</b></p>
        <div class="history-prices"><div><span>Giá tham chiếu trong thư đầu</span><b>${price(r.reference_price)}</b></div><div><span>Giá đóng cửa ${day(r.price_date)}</span><b>${price(r.latest_price)}</b></div><div><span>Biến động so với giá báo tin</span><b class="${tone(r.price_change_pct)}">${pct(r.price_change_pct)}</b></div></div>
        <details><summary>Xem các lần gửi và điều chỉnh</summary><ol>${timeline(r.timeline)}</ol></details></article>`).join('')}</div>
      <p class="history-note">Biến động giá = (giá đóng cửa / giá tham chiếu trong thư đầu − 1) × 100%. Đây là mức tăng/giảm để theo dõi khuyến nghị; chưa có bằng chứng khớp lệnh để tính lãi/lỗ thực nhận. Chưa tính phí, thuế, cổ tức và quyền.</p>
      <details><summary>Nguồn và cách ghi nhận lịch sử</summary><p>Đã đối chiếu thư Gmail và nhật ký gửi StockRadar. Ngày phát hiện, ngày gửi và ngày nhập lịch sử được lưu riêng. DCM buổi chiều là lần cập nhật của khuyến nghị buổi sáng. Email cũ được giữ nguyên nội dung, không xem là điểm mua mới hôm nay.</p><p>Rà soát thư đến ${day(data.mail_search_through)}; nhập lịch sử ${time(data.audit_at)}. “Chưa có email bán” chỉ phản ánh thư đã tìm được, chưa xác nhận nên tiếp tục giữ. Giá tham chiếu trong thư có thể khác giá khớp được sau lúc gửi.</p><p>Các cảnh báo đã gửi dùng Gmail; trạng thái kênh Premium mới trên website được theo dõi riêng.</p></details>
      <section class="history-month" id="review-2026-08"><h2>Rà soát từng ngày tháng 8/2026</h2><div data-month-review role="status">Đang tải kết quả rà soát…</div></section>`;
  }
  function renderReview(data) {
    if (data.schema_version !== 'TECHNICAL_EOD_REVIEW_V1') throw new Error('Sai định dạng rà soát');
    const mount = target.querySelector('[data-month-review]');
    const s = data.summary;
    mount.removeAttribute('role');
    mount.innerHTML = `<p><b>${s.sessions} phiên · ${s.candidate_tickers} mã · ${s.candidate_occurrences} lần đạt bước lọc kỹ thuật và khối lượng.</b> Chưa xác minh đủ 4 lớp để gọi là khuyến nghị mua.</p>
      <p class="history-note">Đây là kết quả tính lại vào ${day(data.generated_at)}, không phải các khuyến nghị đã gửi trong tháng 8. Giá và chỉ báo chỉ dùng dữ liệu đến từng ngày xét.</p>
      <p><b>Chưa thấy điều kiện thoát kỹ thuật đến ${day(data.as_of_date)}:</b> ${s.without_technical_exit_tickers.map(esc).join(', ')}. Danh sách này chưa phải đề nghị mua hoặc giữ hiện tại.</p>
      <details><summary>4 lớp phân tích: phần đã kiểm tra và phần còn thiếu</summary><ul><li><b>4M:</b> chưa đủ hồ sơ tại từng ngày để xác minh chất lượng doanh nghiệp và định giá.</li><li><b>CANSLIM:</b> chưa đủ thời điểm công bố tăng trưởng lợi nhuận, tổ chức nắm giữ và bối cảnh thị trường.</li><li><b>Kỹ thuật SEPA/VCP:</b> kiểm tra xu hướng MA, vùng cản 20 phiên và khoảng cách giá; chưa xác nhận toàn bộ mẫu hình VCP.</li><li><b>Dòng tiền VPA:</b> kiểm tra giá tăng tối thiểu 2%, khối lượng so với 20 phiên trước và phiên giảm trong 10 phiên trước; thanh khoản trung bình tối thiểu 500.000 cổ phiếu/phiên.</li></ul><p>Ngắn hạn đã rà soát kỹ thuật. Các khung 3–6 tháng, 12 tháng và tích sản chưa có đủ dữ liệu tại từng ngày để đánh giá lại.</p><ul>${data.limitations.map(x=>'<li>'+esc(x)+'</li>').join('')}</ul><p>MA là giá trung bình của số phiên tương ứng. Ngày nghỉ theo <a href="${esc(data.calendar_source)}" target="_blank" rel="noopener noreferrer">thông báo giao dịch KIS</a>.</p></details>
      <div class="history-filters"><label>Mã cổ phiếu <select data-history-ticker><option value="">Tất cả mã</option>${[...new Set(data.items.map(r=>r.ticker))].sort().map(t=>`<option>${esc(t)}</option>`).join('')}</select></label><label>Kết quả theo dõi <select data-history-state><option value="">Tất cả</option>${Object.entries(exit).map(([v,l])=>`<option value="${v}">${l}</option>`).join('')}</select></label></div>
      <div data-review-rows></div>
      <details><summary>Lịch đủ 31 ngày và số mã kiểm tra từng phiên</summary><div class="history-scroll"><table><thead><tr><th>Ngày</th><th>Có dữ liệu / 405</th><th>Đủ lịch sử ≥252 phiên</th><th>Mã đạt bước lọc</th></tr></thead><tbody>${data.days.map(d=>`<tr><td>${day(d.date)}</td><td>${d.status==='WEEKEND'?'Cuối tuần':d.status==='HOLIDAY'?'Nghỉ lễ':d.available + ' / 405'}</td><td>${d.status==='REVIEWED'?d.evaluated:'—'}</td><td>${d.candidates.length ? d.candidates.map(esc).join(', ') : d.status==='REVIEWED'?'Không có':'—'}</td></tr>`).join('')}</tbody></table></div><p>Mã thiếu phiên không được tự điền giá hoặc xem như đã đạt. ${data.invalid_bars_excluded} dòng giá không hợp lệ bị loại khỏi toàn bộ dữ liệu đầu vào.</p></details>`;
    function rows() {
      const ticker=mount.querySelector('[data-history-ticker]').value, status=mount.querySelector('[data-history-state]').value;
      const items=data.items.filter(r=>(!ticker || r.ticker===ticker) && (!status || r.status===status));
      mount.querySelector('[data-review-rows]').innerHTML=`<p aria-live="polite">${items.length} lần đạt bước lọc. Mỗi dòng là một mã tại một ngày, không phải một giao dịch.</p><div class="history-scroll"><table><thead><tr><th>Mã / ngày</th><th>Tín hiệu kỹ thuật</th><th>Giá cuối ngày xét</th><th>Giá ${day(data.as_of_date)}</th><th>Biến động giá*</th><th>Theo dõi sau tín hiệu</th></tr></thead><tbody>${items.map(r=>`<tr><td><b>${esc(r.ticker)}</b><br>${day(r.signal_date)}</td><td>${esc(setup[r.setup])}<small>Khối lượng ${Number(r.volume_ratio).toLocaleString('vi-VN',{maximumFractionDigits:2})} lần trung bình</small></td><td>${price(r.reference_close)}</td><td>${price(r.latest_close)}<small>${day(r.price_date)}</small></td><td class="${tone(r.price_change_pct)}">${pct(r.price_change_pct)}</td><td>${exit[r.status]}${r.technical_exit_date?'<small>'+day(r.technical_exit_date)+'</small>':''}${r.followup_status==='GAPS'?'<small>Có phiên thiếu dữ liệu</small>':''}</td></tr>`).join('')}</tbody></table></div><p class="history-note">* So giá đóng cửa ngày xét với giá đóng cửa mới nhất, kể cả khi đã thấy điều kiện thoát. Không phải lợi nhuận chiến lược; không cộng vào tỷ lệ thắng của khuyến nghị đã gửi.</p>`;
    }
    mount.querySelectorAll('select').forEach(e=>e.addEventListener('change',rows)); rows();
  }
  async function load() {
    try {
      renderObserved(await get('recommendation-history.json'));
    } catch (_) {target.innerHTML='<p role="alert">Chưa tải được lịch sử. <button type="button" data-retry-history>Thử lại</button></p>';target.querySelector('button').onclick=load;return;}
    try {renderReview(await get('recommendation-review-2026-08.json'));}
    catch (_) {target.querySelector('[data-month-review]').textContent='Chưa tải được kết quả tháng 8. Vui lòng tải lại trang.';}
  }
  load();
})();
