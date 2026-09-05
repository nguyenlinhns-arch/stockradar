"""Replace the legacy action-only Radar with an authenticated research workspace."""
import re


def render_radar_page(source):
    main = '''<main id="content" data-live-research-radar>
      <section class="page-heading compact-heading"><div class="container"><h1>Radar HOSE</h1><p>Xếp hạng để theo dõi; điểm cao chưa đồng nghĩa nên mua.</p></div></section>
      <section class="container lr-workspace">
        <div class="lr-metrics"><div><span>Đã rà soát</span><b data-lr-total>—</b></div><div><span>Đủ dữ liệu nghiên cứu</span><b data-lr-ready>—</b></div><div><span>Có dấu hiệu ban đầu</span><b data-lr-initial>—</b></div><div><span>Đã xác nhận mua mới</span><b data-lr-buys>—</b></div></div>
        <div class="lr-updated"><span data-lr-date>Đang kết nối dữ liệu…</span><button type="button" data-lr-refresh>Làm mới</button></div>
        <div class="lr-message" data-lr-message role="status">Đang kiểm tra tài khoản…</div>
        <div data-lr-workspace hidden>
          <div class="lr-tabs" role="group" aria-label="Kiểu xem"><button type="button" data-lr-tab="ranking" aria-pressed="true">Xếp hạng</button><button type="button" data-lr-tab="sectors" aria-pressed="false">Theo ngành</button></div>
          <fieldset class="lr-filters"><legend>Lọc cổ phiếu</legend><label>Mã<input data-lr-search type="search" maxlength="3" placeholder="VD: VHM" autocomplete="off"></label><label>Ngành<select data-lr-sector><option value="">Tất cả ngành</option></select></label><label>Trạng thái<select data-lr-filter><option value="ready">Đủ dữ liệu nghiên cứu</option><option value="all">Toàn HOSE</option><option value="initial">Có dấu hiệu ban đầu</option><option value="buy">Đã xác nhận mua mới</option><option value="missing">Chưa đủ dữ liệu</option></select></label><label>Sắp xếp<select data-lr-sort><option value="score">Điểm tổng hợp</option><option value="technical">Kỹ thuật</option><option value="flow">Dòng tiền</option><option value="change">Tăng giá trong phiên</option><option value="ticker">Mã A–Z</option></select></label><button type="button" data-lr-reset>Xóa lọc</button></fieldset>
          <div data-lr-results data-radar-table></div>
          <div class="lr-pagination" data-lr-pagination><button type="button" data-lr-prev>Trang trước</button><span data-lr-page></span><button type="button" data-lr-next>Trang sau</button></div>
          <section class="lr-detail" data-lr-detail hidden tabindex="-1"></section>
        </div>
        <p class="lr-note">Giá đóng cửa theo ngày ghi nhận. <a href="khuyen-nghi/">Khuyến nghị đã gửi →</a></p>
        <details class="lr-method"><summary>Cách đọc Radar</summary><p>Điểm tổng hợp kết hợp chất lượng doanh nghiệp, tăng trưởng, kỹ thuật, dòng tiền, ngành và rủi ro. Chỉ xếp hạng khi đủ dữ liệu nghiên cứu. Mã thiếu dữ liệu vẫn tra cứu được trong “Toàn HOSE”.</p><p>Dấu hiệu ban đầu chỉ phản ánh giá và khối lượng; cần kiểm tra đủ điều kiện trước khi mua. Các mốc theo dõi trên Radar không phải vùng mua, giá cắt lỗ hay mục tiêu đã phát hành.</p><p data-lr-schedule>Lịch rà soát sẽ hiện sau khi kết nối.</p></details>
      </section></main>'''
    source, count = re.subn(r'<main\b[^>]*>.*?</main>', lambda _: main, source, count=1, flags=re.S)
    if count != 1:
        raise ValueError('Radar main section missing')
    source = re.sub(r'assets/app\.js\?[^"\s]+', 'assets/app.js?v=20260905-live-radar', source)
    source = re.sub(r'assets/public-fallbacks-v4\.js\?[^"\s]+', 'assets/public-fallbacks-v4.js?v=20260905-live-radar', source)
    return source.replace('</head>', '<link rel="stylesheet" href="assets/live-radar-v1.css?v=1"><script src="assets/live-radar-v1.js?v=1" defer></script></head>', 1)
