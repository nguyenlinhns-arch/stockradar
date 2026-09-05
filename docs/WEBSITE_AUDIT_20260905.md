# Rà soát website StockRadar — 05/09/2026

> Bản ghi trước khi sửa UX và checkout. Trạng thái mới nhất nằm trong [Production Product Audit](PRODUCTION_PRODUCT_AUDIT_20260905.md).

**Kết luận: website đã hoạt động, nhưng chưa hoàn thiện và chưa tự động đầu cuối hằng ngày.** AI/nghiên cứu và Radar đang dùng dữ liệu thật. Gửi email Premium, phát hành khuyến nghị hành động mới, thanh toán và cập nhật lịch sử khuyến nghị vẫn có phần bị khóa hoặc cần thao tác.

Kiểm tra trực tiếp khoảng 12:30–12:55 giờ Việt Nam. Mã frontend đang chạy: `e315ed32a5db6be76d87d76d7791578c7cb328ab`. Backend target/stoploss được cập nhật trong lần rà soát này. Các trạng thái dưới đây ưu tiên truy vấn production và lịch sử thực thi, không lấy tài liệu trạng thái cũ làm bằng chứng hoạt động.

## Trạng thái thực tế

| Phần | Kết quả | Bằng chứng / giới hạn |
|---|---|---|
| Website, HTTPS và tuyến chính | Hoạt động | 24/25 URL đã kiểm tra trả HTTP 200. Tuyến cũ `/theo-doi/` trả 404; tính năng theo dõi hiện nằm trong tài khoản. HTTP 200 không tự chứng minh hoàn tất nghiệp vụ. |
| Giao diện | Đạt kiểm thử đang có | CI của frontend hiện tại: 17 trang × 5 kích thước = 85/85. Auth/Radar bằng HTTP fixtures cũng đạt. Trình duyệt có phiên Premium thật tải được Radar 405 mã; không ghi nhận console error/warn trong phiên kiểm tra. |
| Dữ liệu và AI | Đang hoạt động | Production `AI_ONLY_READY`; 405/405 dòng tham chiếu còn hạn, 105 dòng đủ nghiên cứu, 300 dòng chỉ tham chiếu; không có mã ngoài HOSE hoặc mã sai định dạng. Một bộ dữ liệu nhất quán, giá ngày 04/09, nghiên cứu cập nhật 09:54:31 ngày 05/09. |
| Quét dữ liệu và nghiên cứu tự động | Đã có lịch và chuỗi chạy thành công | Thu thập → Research V7 → bundle → cache. Các lượt mới nhất đã thành công. Chưa đủ bằng chứng về độ ổn định đúng giờ của toàn bộ các mốc trong nhiều phiên. |
| Khuyến nghị mua mới | Chưa mở phát hành | 5 dấu hiệu kỹ thuật ban đầu, 0 ứng viên đủ tiêu chí; đồng thời cổng action bị khóa, chưa có manifest active và cache báo cáo action có 0 dòng. Hai điều kiện này độc lập. |
| Email Premium từ hệ thống website | **Chưa bật gửi** | `sending_enabled=false`, `scheduler_enabled=false`; 1 email chờ, 0 SENT, 0 delivery events, 0 activation events. Không có bằng chứng nhận thư qua Resend của hệ thống này. |
| Hạ tầng email | Đã chuẩn bị phần lớn | Hồ sơ provider, sender domain, unsubscribe và bounce/complaint đã được ghi nhận. Điều kiện còn thiếu theo readiness RPC: `COMPLIANCE_APPROVAL_MISSING`. Job cron active không đồng nghĩa worker được phép gửi. |
| Thanh toán | **UI và backend không đồng nhất** | Frontend mở thông tin VPBank/VietQR và cấu hình checkout-ready. Production `billing_gate.checkout_enabled=false`, lý do tạm dừng tới khi có decision feed. Không có checkout request. Thiết kế hiện tại là đối soát/duyệt chuyển khoản thủ công, không phải đối soát ngân hàng tự động. |
| Quyền Premium hết hạn | Có tự động đồng bộ | Cron chạy phút 17 mỗi giờ; truy vấn 2 ngày gần nhất thấy 18 lần thành công. Điều này không chứng minh thanh toán tự động. |
| Lịch sử DCM/VHM và hiệu quả | Có dữ liệu đã đối chiếu; **chưa tự cập nhật hằng ngày** | Dữ liệu công khai lấy từ sổ `track-record/verified-email-alerts.json` và `recommendation-history.json`. Giá đang là 04/09. Không có workflow gọi `build_recommendation_history.py`; rà soát email bán vẫn cần đối chiếu nguồn thư. |
| Đăng ký / khôi phục mật khẩu | Chưa chứng minh E2E email thật trong lần này | Tuyến truy cập và kiểm thử fixture đạt; đăng nhập bằng phiên đã có được xác nhận. Không tạo tài khoản, gửi OTP, đặt lại mật khẩu hoặc xóa tài khoản thật trong lần rà soát này. |
| Vận hành dài hạn | Còn thiếu bằng chứng | Chưa xác minh cảnh báo khi dữ liệu cũ/job lỗi tới người vận hành, bài diễn tập khôi phục backup, nhận thư thật và đối soát giao dịch thật. Không coi việc có mã nguồn là bằng chứng những việc này đã chạy. |

Các email DCM/VHM trước đây đã được đối chiếu từ Gmail trong sổ lịch sử. Chúng **không phải bằng chứng** cho việc worker Resend của website đang bật. Không xóa lịch sử thật chỉ vì bộ gửi mới có 0 SENT.

## Lịch tự động đang cấu hình — giờ Việt Nam

| Công việc | Lịch |
|---|---|
| Thu thập giá HOSE | 10:30, 11:15, 13:30, 14:15, 15:25, thứ Hai–thứ Sáu |
| Nghiên cứu | Sau lượt thu thập thành công; thêm 08:10 và 16:20 các ngày trong tuần |
| Đồng bộ cache / chạy lại | Sau bundle thành công; 08:30, 10:40, 11:25, 13:40, 14:25, 16:30, 20:05 |
| Xử lý thay đổi hành động | 10:35, 11:20, 13:35, 14:20 |
| Bản tin sáng | Producer kiểm tra mỗi 2 phút, chỉ xếp thư trong cửa sổ 09:00–09:30, thứ Hai–thứ Sáu; hiện bị chặn do email chưa bật |
| Worker gửi thư | Cron mỗi 2 phút trong khung 09:00–18:59, thứ Hai–thứ Sáu; cờ cho phép gửi đang tắt |
| Quyền Premium | Phút 17 mỗi giờ |

Lịch hiện tính theo thứ trong tuần, **chưa phải lịch nghỉ giao dịch của sở**. Lịch 09:00 là kế hoạch; kiểm thử chưa chứng minh tất cả người nhận nhận được thư lúc 09:00. Các email tổng kết cuối phiên/tuần có loại dữ liệu và mẫu riêng, nhưng chưa xác minh producer/lịch hoạt động tương ứng.

Lịch sử truy xuất được có hai lượt bootstrap theo schedule lỗi ngày 04/09, sau đó có lượt thành công. Chuỗi research/cache mới nhất cũng đã phục hồi thành công. Không suy ra các lần sửa bằng push/manual thành bằng chứng rằng mọi mốc tự động trong phiên đã đạt SLA.

## Bổ sung target/stoploss theo yêu cầu trong phiên này

Đã triển khai `stock-ai v21`, `stock-ai-guest v20`, `email-worker v8` và migration `preserve_email_horizon_targets`.

- Câu trả lời AI đặt mục tiêu dự kiến ngay sau kết luận: ngắn hạn, 3 tháng, 6 tháng, 12 tháng và ngưỡng tham khảo tích sản.
- Kịch bản tách khỏi target chính thức. Chưa có dự báo EPS kiểm chứng thì công khai giả định mô hình và độ tin cậy thấp; không biến chúng thành khuyến nghị mua.
- Ngắn hạn dùng mốc giá theo dõi, ATR có thật và quy tắc quản trị rủi ro đang có; không điền ATR giả khi thiếu.
- Email giữ các mức `target_near`, `target_3_6m`, `target_12m`, stoploss và thời hạn. Trước khi gửi, lấy lại giá từ đúng báo cáo được phát hành, cùng manifest/snapshot/thời điểm, để không dùng mức cũ trong hàng đợi.
- Chặn email mua/mua thêm nếu thiếu target của đúng thời hạn, thiếu stoploss/vùng vào hoặc các mức nằm sai thứ tự. Email thoát vị thế không bị chặn chỉ vì không còn target mua.
- Không thay đổi cổng gửi mail, phát hành action hoặc thanh toán. Không gửi email thật khi kiểm thử.

Kiểm tra MWG trực tiếp trên website cho thấy mục tiêu ngắn hạn 83.490đ và stoploss giả định 72.105đ chỉ khi giá vào 75.900đ được xác nhận; kịch bản 3 tháng 68.950đ, 6 tháng 69.979đ, 12 tháng 72.083đ. Đây là **đầu ra kiểm thử mô hình**, không phải khuyến nghị giao dịch. Chi tiết công thức và giới hạn nằm trong [quy tắc target dự kiến](TARGET_SCENARIOS_20260905.md).

## Các việc cần hoàn tất trước khi gọi là tự động hằng ngày

1. Hoàn tất điều kiện bật email, rồi thực hiện một lượt gửi được cho phép và đối chiếu provider → webhook → trạng thái nhận. Hiện chỉ có kiểm thử mock/SQL hoàn tác.
2. Đồng bộ trạng thái bán Premium giữa giao diện và backend; hoàn tất đối soát/duyệt thanh toán nếu muốn mở bán.
3. Nối cập nhật giá lịch sử vào pipeline hằng ngày; nối sổ khuyến nghị đã phát hành vào nguồn sự kiện thống nhất. Giá mới không tự chứng minh đã có email bán.
4. Hoàn tất điều kiện phát hành action và tạo báo cáo có target/stoploss theo đúng thời hạn. AI research đang chạy không thay thế bước này.
5. Xác minh các mốc tự động qua ít nhất một phiên đầy đủ, thêm giám sát thiếu dữ liệu/job lỗi, xử lý lịch nghỉ giao dịch và diễn tập khôi phục.

## Kiểm chứng và bảo mật

- 441/441 kiểm thử Python, 44/44 JavaScript đạt sau thay đổi chức năng; production build đạt.
- SQL thử cả trước và sau triển khai: phát hành đúng manifest, hết hạn, dữ liệu tương lai, giữ riêng tư, cuối tuần, quyền/consent, chống trùng và bảo toàn target theo từng thời hạn. Toàn bộ fixture được rollback.
- Quét 590 file theo dõi và 2.074 blob trong lịch sử Git: không phát hiện secret.
- Supabase security advisor: 0 ERROR, 9 WARN. Tám cảnh báo liên quan API SECURITY DEFINER có chủ đích, cần duy trì kiểm tra auth/ownership/allowlist; cảnh báo còn lại là leaked-password protection đang tắt. Không thể ghi “không có cảnh báo”.
- Performance advisor: chỉ có 14 INFO. Hàm helper giá mới không được cấp quyền gọi cho anon/authenticated.

Nguồn trực tiếp: [CI và deploy frontend](https://github.com/nguyenlinhns-arch/stockradar/actions/runs/33945231806), [nghiên cứu V7](https://github.com/nguyenlinhns-arch/stockradar/actions/runs/33940333834), [đồng bộ cache](https://github.com/nguyenlinhns-arch/stockradar/actions/runs/33940395622), truy vấn production Supabase và kiểm tra tại [StockRadar](https://stockradar.vn/). [Giải thích cảnh báo password](https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection).
