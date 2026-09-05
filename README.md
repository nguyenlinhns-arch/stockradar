# StockRadar.vn

Website tiếng Việt cho nghiên cứu cổ phiếu HOSE. Giữ giao diện hiện tại; Python xử lý dữ liệu và quyết định, Supabase lưu cache riêng, Edge Functions phục vụ AI/tài khoản, GitHub Pages phục vụ frontend.

`Nguồn → ETL → Data Layer → nghiên cứu/tín hiệu đã kiểm tra → Web / AI / Email`

Đã kết nối dữ liệu thật của 405 mã HOSE, lịch sử 07/07/2023–04/09/2026. Mock chỉ phục vụ kiểm thử và bị chặn khỏi kết quả công khai. Các tín hiệu hành động vẫn cần đạt cổng phát hành. Xem [trạng thái và chất lượng dữ liệu](docs/UNIFIED_DATA_LAYER.md).

## Chạy và kiểm tra

```sh
python -m pip install pandas
npm ci --ignore-scripts
npx playwright install chromium
python -m unittest discover -s engine/tests -v
node --test engine/tests/ai_runtime.test.mjs engine/tests/ai_handlers.test.mjs
python scripts/build_production.py
python -m http.server 8765 --bind 127.0.0.1 --directory .pages-site
```

Ở terminal khác:

```sh
npm run visual-qa
node scripts/auth_session_qa.cjs
python scripts/scan_secret_history.py
```

Dùng Node 24, Python 3.12+. Build tái hiện các bước biến đổi và kiểm tra của Pages. Auth QA dùng browser và SDK thật với HTTP fixtures, không tạo tài khoản production.

## Dữ liệu và triển khai

- `engine/stockradar/data_layer.py`: chuẩn hóa CSV/JSON/XLSX/Parquet, kiểm tra HOSE/OHLCV, lưu lịch sử SQLite có index và chỉ số dùng chung. XLSX/Parquet cần engine đọc định dạng tương ứng.
- `scripts/build_data_layer.py`: dựng dữ liệu từ một lần chạy nguồn HOSE, giữ lịch sử đầy đủ ở backend.
- `research-decision-v7.yml` → `publish-internal-research-bundle.yml` → `sync-stockradar-research-cache.yml`: chuyển dữ liệu và nghiên cứu cùng lượt chạy vào backend bằng GitHub OIDC.
- `supabase/functions/_shared/`: dữ liệu, định tuyến câu hỏi và diễn giải dùng chung cho guest/tài khoản.
- `supabase/tests/unified_quota.sql`: kiểm thử quota DB, rollback toàn bộ fixture.
- `.github/workflows/pages.yml`: kiểm thử, build, QA đa kích thước và deploy khi push main.

Giữ dữ liệu nguồn, khóa API và lịch sử riêng trong thư mục Git bỏ qua hoặc server secrets. Không commit .env, service-role key, vị thế hay danh sách ưu tiên riêng.
