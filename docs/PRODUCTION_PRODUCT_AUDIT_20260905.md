# Production Product Audit — StockRadar — 05/09/2026

**Kết luận: chưa hoàn thiện và chưa tự động đầu cuối. Chưa sẵn sàng chạy Ads hoặc mở thu phí Premium mới.** Website có dữ liệu nghiên cứu thật và chuỗi thu thập theo lịch; phần phát hành hành động, gửi email và thanh toán còn bị khóa. Bản sửa này củng cố sản phẩm đang chạy, không tạo dữ liệu để làm đầy giao diện.

Phạm vi kế thừa: Product Spec/V2, Email, Analytics, Recommendation Schema/Lifecycle, Track Record, Build Status, Premium Readiness và Production Gate Activation Runbook; các tuyến public/auth/account, engine, Edge Functions, migrations và bộ regression hiện có. Không thay kiến trúc GitHub Pages + Supabase + Python engine.

## DONE — đã sửa và kiểm thử

| Hạng mục | Thay đổi và bằng chứng |
|---|---|
| P0.1 Session | AI giữa các tuyến dùng chung Supabase client và khóa lưu phiên `stockradar-auth`. Fixture Free/Paid kiểm tra đăng nhập → Home → tải lại → Radar/AI → quay lại → đăng xuất. Tải lại không làm mới quota. Phiên Premium thật đã được kiểm tra ở đợt audit trước. |
| P0.2 Nguồn/ngày dữ liệu | Home dùng readiness RPC; phân biệt ngày đóng cửa và thời gian nghiên cứu. Thanh trạng thái dưới hero được giữ qua cả script chạy sau tải trang. Không ghi LIVE cho EOD. Mất API hoặc dữ liệu hết hạn chuyển UNAVAILABLE. |
| P0.3 Decision Card | Hai endpoint AI và hai renderer dùng cùng thẻ: kết luận trước, giá/ngày/nguồn, vùng mua, tỷ trọng, stoploss, target gần/3–6/12 tháng, upside/downside, R/R; lý do ngắn và phân tích đầy đủ có thể mở rộng. Setup/MA10/50/150/200/pivot/volume/RVOL/VPA hiển thị khi có bằng chứng. |
| Điều kiện mua | Hành động phải cùng ticker, thời hạn, snapshot và báo cáo được phép phát hành. Chặn báo cáo stale/future/mock và kế hoạch mua thiếu hoặc sai vùng vào, stop, target, R/R, setup, tỷ trọng. Kiểm tra tỷ trọng theo ba tầng đã có; không điền tỷ trọng giả. Làn bán/giảm độc lập không bị khóa chỉ vì thiếu target mua. |
| Target ước tính | Research có mô hình tham khảo ngay trong thẻ, ghi độ tin cậy thấp, giả định/công thức và điều kiện kích hoạt. Không biến target mô hình thành target được phát hành. Stop ngắn hạn gắn giá vào giả định; không dùng chung cho 3–6/12 tháng/tích sản. Xem [TARGET_SCENARIOS_20260905.md](TARGET_SCENARIOS_20260905.md). |
| P0.4 Production binding | Giữ cổng publication/manifest/snapshot/data rights/compliance. Không bật cổng khi dữ liệu thiếu. Context cũ bị loại trước khi gửi tới model hoặc tính kịch bản. Các trường thiếu được ghi rõ. |
| P0.5 Email | Subject có setup/hành động, giờ và ngày VN, giá. Đầu thư là hành động, sau đó target theo thời hạn, stoploss, tỷ trọng, R/R, nguồn và điều kiện đánh giá lại. Worker lấy lại giá từ báo cáo chuẩn ngay trước gửi. Mua/ADD thiếu target/stop/vùng vào hoặc setup/tỷ trọng/RR bị chặn trước provider. Email thoát vị thế không bắt buộc target mua. |
| P0.6 Quota | Guest 3, Free 10/ngày VN, Paid không giới hạn ngày. Thêm giới hạn kỹ thuật riêng 30 yêu cầu/phút cho tài khoản; Paid gặp giới hạn này nhận thông báo chờ, không bị dẫn tới nâng gói. SQL rollback thử quyền, quota và tài khoản suspended. |
| P0.7 Checkout | Sửa lỗi UI từng hiện QR trong khi backend khóa bán. HTML bắt đầu đóng, không có số tài khoản/QR điền sẵn. RPC readiness mới xác minh cả sản phẩm, email, billing; backend tạo checkout cũng kiểm tra cùng cổng. “Đã chuyển khoản” chỉ thành chờ đối soát. Chỉ server xác nhận PAID mới nâng quyền; menu cập nhật không cần đăng nhập lại. |
| P0.8 Hiệu quả | Có bộ tổng hợp riêng cho LIVE_PUBLISHED/DECISION_GRADE, loại mock/replay/email lịch sử, giữ cả lỗ, mở, chưa kích hoạt, đã đóng và chống trùng ID. Mẫu dưới 20 lệnh đóng ghi chưa đủ mẫu; ngưỡng này không phải chứng minh ý nghĩa thống kê. Không tính drawdown khi chưa có đường vốn. |
| P1 Home/mobile | Hero AI-first, hai CTA; menu AI StockRadar/Khuyến nghị/Hiệu quả/Theo dõi/Premium và tài khoản riêng. Tối đa ba tín hiệu được phát hành, không tạo card bù chỗ trống. Bỏ sidebar lặp và giảm tài nguyên Home xuống khoảng 148 KB CSS/JS nội bộ (giới hạn 196 KB; không gồm SDK tải động). |
| P1 Analytics | Ghi tương tác AI, báo cáo hữu ích, kích hoạt Free sau kết quả đủ mới và checkout sau khi server tạo thành công. D1/D7 là lượt phân tích hữu ích trở lại ở mức trình duyệt, không tự coi là retention theo tài khoản. Link email có attribution loại thư, không có định danh người nhận. Không truyền hội thoại, holdings hay credentials. |
| P1 Build/SEO | Asset URL gắn hash nội dung sau mọi bước build để người dùng nhận bản JS/CSS mới. SEO chỉ index 7 tuyến phù hợp, trang tài khoản/thanh toán/cổ phiếu động noindex. Khôi phục tuyến cũ /theo-doi/ chuyển tới tài khoản. Luồng full CI sở hữu deploy tự động; fast-hotfix chỉ chạy thủ công, dùng chung hàng đợi Pages để tránh đè bản. |

Phân tích 4M, CANSLIM, SEPA/VCP, VPA, định giá đa phương pháp, Bear/Base/Bull và probability gate được kế thừa. “Hỗ trợ phương pháp” không có nghĩa từng mã đã có đủ EPS dự phóng, FCF/Owner Earnings, DCF hoặc dữ liệu ngành để phát hành target. Không lấy score làm xác suất.

## TESTING — cần bằng chứng chạy thực

- Đăng ký mới, khôi phục mật khẩu/email nhận thực tế và vòng đời thanh toán thật chưa được thử trong đợt này. Fixture trình duyệt không thay thế bằng chứng nhận thư hoặc tiền vào.
- Chuỗi intraday đã có lịch, nhưng chưa đối chiếu đủ một phiên thực tại cả bốn mốc với cùng snapshot, same-time/progress-adjusted volume và độ trễ. Không lấy EOD volume làm bằng chứng scanner intraday đã hoạt động.
- Thêm Pages schedule 16:45 VN thứ Hai–thứ Sáu để cập nhật giá theo dõi email lịch sử từ artifact thu thập HOSE sau 15:25, đã chạy thành công trên main. Chỉ dùng một file OHLCV không mơ hồ, chặn giá tương lai/cũ, giữ nguyên sự kiện email và nghiên cứu lịch sử có ngày. Bộ chọn artifact đã có unit test; **lượt schedule đầu tiên chưa diễn ra**. Không đọc mailbox hoặc tự thêm email bán.
- Attribution email CTA chỉ chứng minh truy cập từ link; chưa chứng minh delivered/open/click của provider. Signup/payment/renewal phải đối chiếu sự kiện server; chưa có funnel production xuyên suốt và số liệu D1/D7 đủ thời gian.

## BLOCKED — trạng thái production đã truy vấn

Kiểm tra trực tiếp 14:05 giờ VN ngày 05/09; đây là trạng thái thực tế, độc lập với test PASS.

| Phụ thuộc | Kết quả | Điều kiện để hoàn tất |
|---|---|---|
| Decision feed | AI_ONLY_READY; 405 dòng HOSE, 105 đủ nghiên cứu, 300 chỉ tham chiếu. Giá 04/09, nghiên cứu cập nhật 09:54:31 ngày 05/09. Cổng action tắt, chưa có active manifest, cache báo cáo action 0 dòng. | Dataset được duyệt quyền sử dụng/compliance, manifest active và báo cáo DECISION_GRADE đủ kế hoạch theo từng thời hạn. |
| Email Premium | Provider/domain có hồ sơ phê duyệt; readiness còn COMPLIANCE_APPROVAL_MISSING. Cổng gửi và scheduler_enabled vẫn false; 1 pending, 0 sent, 0 delivery events. Cron active không có nghĩa đang gửi. | Hoàn tất phê duyệt và kích hoạt có kiểm soát; sau đó thử một thư được phép và đối chiếu provider → webhook → trạng thái. |
| Checkout | Readiness PAUSED; billing_ready/product_ready/email_ready/checkout_ready đều false. | Hoàn tất các cổng trước khi mở bán. Hệ thống hiện đối soát VietQR thủ công; không tuyên bố đối soát ngân hàng tự động. |
| Track record production | Không có cohort LIVE_PUBLISHED thực đang chạy. Sổ email lịch sử được giữ riêng. | Nối journal phát hành thực vào bộ xuất public, theo dõi activation/exit và đường vốn/benchmark; đủ mẫu mới công bố thống kê. Phần tổng hợp đã có code, exporter live đầu cuối chưa được chứng minh hoạt động. |
| Vận hành lâu dài | Lịch theo thứ trong tuần, chưa phải lịch nghỉ của sở; chưa có bằng chứng SLA dài ngày, cảnh báo lỗi đến người vận hành hoặc diễn tập khôi phục. | Đối chiếu ít nhất một phiên đầy đủ; bổ sung lịch nghỉ, cảnh báo, kiểm tra phục hồi/backup bằng bằng chứng. |
| Bảo mật Auth | Leaked-password protection đang tắt. | Bật cấu hình được tài khoản Supabase hỗ trợ và kiểm tra lại. Không thay mật khẩu/tài khoản thật trong đợt audit. |

Không gửi thư thật, không tạo giao dịch thanh toán và không thay đổi cờ gửi/bán/phát hành để làm kiểm thử. Các fixture SQL đều rollback. Các email đã đối chiếu trước đây vẫn là lịch sử thật; 0 SENT của worker mới không xóa bằng chứng đó.

## Lịch hiện có — giờ Việt Nam

| Công việc | Lịch |
|---|---|
| Thu thập HOSE | 10:30, 11:15, 13:30, 14:15, 15:25 các ngày trong tuần |
| Research | Sau thu thập thành công; thêm 08:10, 16:20 |
| Đồng bộ cache | Sau bundle thành công; thêm 08:30, 10:40, 11:25, 13:40, 14:25, 16:30, 20:05 |
| Xử lý thay đổi hành động | 10:35, 11:20, 13:35, 14:20; xử lý sau collector, không được gọi là scanner chạy đúng phút |
| Daily 09:00 | Producer trong cửa sổ 09:00–09:30; hiện khóa |
| Worker | Mỗi 2 phút 09:00–18:59; hiện khóa |
| Quyền Paid hết hạn | Phút 17 mỗi giờ |
| Giá theo dõi email lịch sử | Pages 16:45 mới bổ sung; TESTING cho tới khi có run thực |

## Kiểm chứng và release

- Python: **445/445**; Node: **57/57**.
- UI: 17 tuyến × 5 kích thước 360/390/430/768/1440; kiểm tra auth Free/Paid và Radar; bổ sung 8 trường hợp Decision Card/checkout, XSS, stale data, menu/thanh trạng thái sau runtime và privacy analytics.
- SQL: quota + product readiness + recommendation/email gating PASS, rollback; bao gồm manifest, expiry, future data, privacy, cuối tuần, consent revocation, dedupe.
- Build production và các giới hạn tài nguyên/copy PASS. Test browser dùng fixture được ghi rõ, không tạo sự kiện tài chính hoặc thư giả trên production.
- Security advisor: 0 ERROR, **11 WARN** (10 cảnh báo thực thi SECURITY DEFINER theo role có chủ đích; 1 leaked-password protection tắt), 28 INFO. RPC readiness mới chỉ trả boolean và timestamp, không trả cấu hình thanh toán hoặc token. [Giải thích quyền SECURITY DEFINER](https://supabase.com/docs/guides/database/database-linter?lint=0028_anon_security_definer_function_executable), [password protection](https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection).
- Quét secret: 608 file theo dõi và 2.093 Git blob, 0 phát hiện; artifact dữ liệu nguồn/ảnh QA không đưa vào commit.
- Backend đã triển khai: stock-ai **v23**, stock-ai-guest **v22**, email-worker **v9**, giữ xác thực tùy chỉnh đang dùng. Migrations `20260905101001_preserve_email_horizon_targets.sql` và `20260905101002_align_product_readiness_and_action_email.sql` đã áp dụng.
- Frontend: bản sửa được gửi qua [workflow Verify and deploy StockRadar Pages](https://github.com/nguyenlinhns-arch/stockradar/actions/workflows/pages.yml). Trạng thái run/SHA và kiểm tra sau deploy được ghi bổ sung khi workflow hoàn tất.

[Website production](https://stockradar.vn/) · [Audit ban đầu, trước sửa](WEBSITE_AUDIT_20260905.md) · [Runbook điều kiện mở production](PRODUCTION_GATE_ACTIVATION_RUNBOOK_20260905.md)
