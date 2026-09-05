# Data Layer và kiểm chứng — 05/09/2026

## Nguồn và chất lượng

Nguồn chính là các file mới nhất trong Google Drive `Chứng khoán / 04 - Dữ liệu StockRadar`: OHLCV daily, technical postclose, fundamental ratios postclose và valuation bootstrap. Chọn bản canonical OHLCV mới hơn bản POSTCLOSE trùng kích thước. File CSV gốc nằm trong `private-staging/`, không được commit. ETL ghi SHA-256 từng file, vai trò nguồn và snapshot ID.

Nghiên cứu V7 hiện có cung cấp sector/market, 4M/payback, quyết định, risk/reward, tin HOSE và sự kiện doanh nghiệp. Chi tiết được ghép vào cùng context; frontend và LLM không chạy mô hình tín hiệu riêng. Vị thế chỉ đọc theo user ID đã xác thực và chỉ gửi những vị thế liên quan đến câu hỏi của chính tài khoản đó.

| Kiểm chứng | Kết quả |
|---|---:|
| Mã trong danh sách HOSE đã kiểm tra | 405 |
| Dòng lịch sử nguồn | 292.224 |
| Dòng OHLCV hợp lệ | 292.194 |
| Khoảng ngày quan sát | 07/07/2023–04/09/2026 |
| Dòng cách ly do OHLC/volume lỗi | 30, thuộc 26 mã |
| Mã đủ điều kiện ghép chi tiết vào snapshot 04/09 | 355 |
| Mã có ngày giao dịch cuối cũ hơn | 24 |

Thiếu dữ liệu không thành số 0. API phân biệt `updated`, `stale`, `error`; chỉ ghép khi trùng ngày và giá. `as_of_date` là ngày quan sát; `updated_at` của ETL là lúc xử lý, có `updated_at_basis`, không phải giá realtime. Thời gian của context nghiên cứu được giữ nguyên. Cache chọn bản mới nhất, không ưu tiên bản ready cũ hơn.

Lịch sử đầy đủ nằm trong SQLite với index `(ticker,date)`. Context chỉ mang 20 bar gần nhất, phạm vi lịch sử và chỉ số đã tính. Quét server giới hạn tối đa 10 mã, mặc định 5, chỉ HOSE và Vol20 ≥ 500.000. Pocket Pivot/Breakout lấy trạng thái của engine, không suy ra chỉ từ volume lớn.

RVOL cuối phiên = volume/Vol20; không chọn giá trị dự phóng giữa phiên. Thiếu same-time history trả `null`. Lớp chi tiết hiện là dữ liệu cuối phiên; xác nhận intraday còn phụ thuộc nguồn cùng thời điểm và cổng chất lượng của engine.

Định giá bootstrap là sơ bộ, chưa có giả định được xác minh. MOS = (Fair Value − Price)/Fair Value, khác upside. EPS/LNST growth, xác suất thắng và đánh giá định tính chưa đủ nguồn vẫn để thiếu. Confidence không được trình bày thành xác suất thành công.

## Tài khoản và kiểm thử

- Guest: production cho phép 3 lượt/ngày Việt Nam; lượt thứ tư trả 429 dù đổi guest ID. Identity dùng HMAC từ IP do proxy cung cấp; cùng mạng dùng chung hạn mức. Proxy từ chối yêu cầu giả mạo header IP.
- Free: transaction DB cho phép đúng 10/11 lượt. Paid: 15/15 lượt được phép, `limit` và `remaining` là `null`. Fixture được rollback, không ảnh hưởng tài khoản thật.
- Browser/SDK thật với HTTP fixtures: Free/Paid đăng nhập về trang chủ, reload, đi trang khác rồi về, giữ quota, đăng xuất và không phục hồi token cũ. Đây không phải kiểm chứng email đăng ký production.
- Một client Supabase dùng chung, chuyển legacy storage một lần. Header chỉ có một module sở hữu, so sánh HTML đã chuẩn hóa để tránh vòng lặp tạo lại nút Đăng xuất.
- Kiểm thử Python, thực thi handler AI và QA 17 trang tại 1440/768/430/390/360 px. Pages chạy lại trước deploy.

## Vận hành và giới hạn còn lại

Edge Functions AI và đồng bộ đã triển khai. AI có dữ liệu thật cho mã, Top, Pocket Pivot, gần breakout và so sánh. OpenAI trả `429 CREDIT_BALANCE_EXHAUSTED`; hệ thống dùng StockRadar Core và ghi `READY_FALLBACK`. Khôi phục model cần bổ sung số dư ở [OpenAI API billing](https://platform.openai.com/settings/organization/billing); gói ChatGPT không thay thế số dư API.

Email giữ pipeline và quyền Paid hiện có, dùng snapshot/tín hiệu đã phát hành của cùng engine. Daily và intraday vẫn chịu cổng gửi, chất lượng dữ liệu và sự đồng ý nhận email. Resend domain pending; DNS `resend._domainkey` và `send` chưa tồn tại. Chưa thể kiểm chứng gửi thư thật; cổng gửi chưa mở.

Public Action, active production manifest và các cổng phát hành chưa đạt. Top trong AI là xếp hạng nghiên cứu; khối khuyến nghị công khai không được điền dữ liệu mẫu hoặc coi là tín hiệu mua đã phát hành. BCTC loại khoản bất thường, định tính quản trị/moat, same-time history đầy đủ và giả định định giá vẫn cần bổ sung để nâng chất lượng quyết định.

Đã quét source Git theo dõi và toàn bộ blob lịch sử có thể truy cập bằng các mẫu private key, API token và service-role JWT; không có kết quả khớp. Đây không phải bảo đảm phát hiện mọi dạng bí mật. Dữ liệu cá nhân và khóa production không được đưa vào báo cáo.
