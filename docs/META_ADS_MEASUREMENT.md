# StockRadar Free registration measurement

Updated 06/09/2026. **TESTING / BLOCKED — chưa ADS READY.**

| Phần | Trạng thái hiện tại |
|---|---|
| Browser integration | DONE code; fixture kiểm tra mapping, privacy, dedupe và script bị chặn |
| Pixel production | **BLOCKED — META_PIXEL_ID_NOT_CONFIGURED** |
| CompleteRegistration trong Events Manager thật | **TESTING — chưa có bằng chứng, không PASS** |
| Server CAPI | **CAPI_NOT_CONFIGURED**; mới có interface receipt/event_id, chưa gửi CAPI |
| AI model production | **BLOCKED — MODEL_CREDIT_BLOCKED**, provider trả `OPENAI_429_CREDIT_BALANCE_EXHAUSTED` |
| Auth email ngoài team | **BLOCKED — SMTP production chưa được xác minh**, xem audit |

## Cấu hình Pixel

Trong GitHub repository `nguyenlinhns-arch/stockradar`, đặt Actions **repository variable** `META_PIXEL_ID` bằng ID của Pixel/dataset đã chọn. Chạy lại workflow **Verify and deploy StockRadar Pages**. `scripts/build_pages.py` sinh một cấu hình công khai duy nhất trong `assets/auth-config.js`:

```js
window.STOCKRADAR_META_CONFIG = Object.freeze({enabled: true, pixelId: 'PIXEL_ID'});
```

Không điền placeholder ở trên vào production. ID rỗng hoặc không hợp lệ làm integration tắt yên lặng. Bỏ variable rồi deploy lại để tắt. Không đưa `META_ACCESS_TOKEN`, khóa Supabase đặc quyền hoặc thông tin đăng nhập vào repository variable công khai này.

SDK async, tải khi có cấu hình; không chặn AI/signup. Tắt auto-configuration, không gửi advanced matching. DNT/GPC, user-agent bot đã biết, URL/referrer mang token/PII hoặc query ngoài danh sách cho phép làm Pixel bỏ qua trang. Không cố gửi lại khi script bị chặn. Trong Events Manager, cũng phải tắt automatic events/automatic advanced matching và kiểm tra payload thực tế trước khi mở Ads. Website vẫn hoạt động khi không có Pixel hoặc trình duyệt chặn SDK.

## Event và thẩm quyền

| Canonical event | Meta | Khi ghi nhận |
|---|---|---|
| Page navigation | `PageView` | Mỗi page load; không phải chỉ số hoàn tất đăng ký |
| `landing_view` | Không gửi thêm PageView | Một landing/session/path; chỉ Home hoặc landing organic |
| `ai_question_started` | `AIQuestion` custom | Gửi câu hỏi; chỉ tier, ticker hợp lệ, horizon, source_page |
| `ai_result_success` / `ai_result_failed` | Không mapping | Success cần READY + MODEL_READY + answer không rỗng |
| `ai_guest_first_result` | Không mapping | Guest nhận kết quả mô hình thành công đầu tiên |
| `guest_free_cta_impression` / `guest_free_cta_click` | Không mapping | CTA Free dưới kết quả, nhắc còn1/hết lượt; không hiện cho Free/Premium |
| `signup_started` | `StartRegistration` custom | Focus/input đầu tiên, một lần/form flow trong session |
| `signup_submitted` | Không mapping | Sau validation, trước request Auth; không phải conversion |
| `signup_verification_requested` | Không mapping | Auth chấp nhận và yêu cầu xác minh; có thể là phản hồi giữ kín email đã tồn tại |
| `signup_completed` | `CompleteRegistration` standard | Chỉ receipt từ **auth.users INSERT thật** khớp user và flow của request được chấp nhận |
| `login_success` | Không mapping | Đăng nhập thành công; tier chưa biết để null, không đoán Premium/Free |
| `return_to_ai_after_registration` | Không mapping | Tài khoản đã đăng nhập gửi câu AI sau đăng ký, một lần/receipt trong browser |
| `premium_view`, `checkout_started`, `payment_submitted` | Không mapping | Giữ funnel nội bộ; chưa tối ưu Ads Premium |
| `premium_activated` | Không mapping | Server quan sát subscription grant có payment PAID đã verified; không thể tự báo từ browser |

Legacy `home_view`, `signup_start`, `signup_submit`, `signup_complete`, `pro_view`, `pricing_view`, `checkout_created` được adapter chuẩn hóa. Các alias impression/start dùng chung khóa chống trùng. Browser không được tự ghi `signup_completed` hoặc `premium_activated` vào API. V1 history được giữ nguyên, không gộp vào KPI V2.

`signup-link` vẫn gọi **public Auth signUp**, bắt buộc email verification, không auto-login/auto-confirm hay tự cấp Premium. Supabase có thể trả user giả cho email đã tồn tại; vì thế HTTP thành công chưa đủ. Trigger riêng tạo receipt khi Auth INSERT; RPC server chỉ chấp nhận receipt đúng user/flow trong24 giờ. Retry trả cùng UUID. Chỉ response `registration_created:true` kèm UUID mới kích hoạt Pixel. Browser dùng UUID này làm `eventID`, chống trùng bằng localStorage; server có unique index và transaction để chỉ lưu một lần. Xác minh email cập nhật `verified_at`, không phát CompleteRegistration lần nữa. Nếu lưu measurement thất bại, đăng ký vẫn tiếp tục nhưng conversion không được suy đoán.

Nguồn tham khảo: [Supabase signUp](https://supabase.com/docs/reference/javascript/auth-signup), [Meta conversion tracking](https://developers.facebook.com/docs/meta-pixel/implementation/conversion-tracking/), [Meta Pixel/server deduplication](https://developers.facebook.com/docs/marketing-api/conversions-api/deduplicate-pixel-and-server-events/). Trang Meta trả429 trong phiên triển khai; cấu hình Events Manager và payload thực cần xác minh bằng tài khoản Meta trước mở Ads.

## Attribution và privacy

Giữ `utm_source`, `utm_medium`, `utm_campaign`, `utm_content`, `utm_term` và `fbclid` trong first/last touch tối đa30 ngày ở browser. Điều hướng nội bộ/callback Auth không ghi đè campaign. UTM giới hạn120 ký tự, cho phép chữ/số và dấu an toàn; loại URL, email, token và giá trị bất thường. Campaign phải là tên chiến dịch, không phải thông tin khách hàng. `fbclid` giới hạn ký tự/độ dài, lưu browser để dành cho interface tương lai; không đưa vào analytics payload hoặc tự xây navigation URL từ nó.

Payload tự gửi Meta không chứa email, mật khẩu, OTP, user ID, JWT, Supabase token, holdings, câu hỏi/answer, thông tin ngân hàng hoặc payment reference. CompleteRegistration chỉ chứa loại tài khoản, content_name, nguồn và năm UTM đã sanitize. Meta SDK có hoạt động mạng/cookie riêng; không thể chứng minh privacy production chỉ bằng kiểm thử stub. Đối chiếu request trong trình duyệt/Events Manager thật trước mở.

Analytics nội bộ dùng UUID session ngẫu nhiên được server băm với khóa riêng. IP kết nối chỉ tạo hash đổi mỗi ngày cho giới hạn chống lạm dụng60 events/phút; không lưu/gửi IP raw tới Meta. UA crawler/bot/Headless/preview và localhost bị loại. Honeypot/validation/Auth rate limit chặn signup không hợp lệ. UA filtering không chứng minh loại được bot giả trình duyệt người; cần đối chiếu verified accounts và bất thường campaign khi có traffic thật.

Không đồng nhất browser session với một người. Xóa storage, chặn tracking, mở sang WebView/trình duyệt khác có thể mất liên kết browser hoặc làm thiếu conversion. Auth callback qua SDK giữ session khi hợp lệ; thiếu verifier/session dẫn về login có hướng dẫn. Không copy token giữa ứng dụng và không tắt verification để tăng conversion.

## Interface CAPI tương lai

`private.registration_conversion_receipts` giữ event_id ổn định, thời điểm accepted/verified và `capi_status=CAPI_NOT_CONFIGURED`. Hiện không có endpoint gửi CAPI hay retry worker giả. Sau này server sender phải dùng **cùng** `event_name=CompleteRegistration` và `event_id` của receipt với Pixel, idempotent retry, giữ Meta access token ở server secret/Vault và chỉ bật khi có Pixel ID + token hợp lệ. Phải kiểm thử deduplication trong Events Manager trước đổi nhãn thành `BROWSER_PIXEL_READY`; nhãn này không đồng nghĩa CAPI đã hoạt động.

## Test Events bắt buộc trước Ads

1. Mở Events Manager → dataset/Pixel đúng → Test Events; ghi lại thời gian và browser thử.
2. Mở `https://stockradar.vn/?utm_source=facebook&utm_medium=paid_social&utm_campaign=free_launch` từ công cụ test; xác nhận PageView.
3. Hỏi một mã HOSE; xác nhận AIQuestion chỉ có bốn metadata cho phép. Model phải trả MODEL_READY thật trước khi đánh giá giá trị funnel.
4. Nhấn CTA Đăng ký Free dưới kết quả; URL phải là `signup/?plan=free`, attribution còn nguyên.
5. Tương tác form; StartRegistration đúng một lần dù focus nhiều trường.
6. Thử validation sai/backend từ chối/email tồn tại/honeypot: không CompleteRegistration.
7. Tạo một tài khoản Free mới có email do người thử kiểm soát; đối chiếu receipt AUTH_SERVER và **đúng một** CompleteRegistration với cùng eventID. Không ghi email trong bằng chứng chia sẻ.
8. Reload, back/forward, retry cùng receipt và mở email verification: không thêm CompleteRegistration.
9. Xác minh, về Home, header Free, quota10, reload và hỏi tiếp vẫn dùng session. Nếu email mở browser khác, đăng nhập bằng flow hướng dẫn; không redirect loop.
10. Lặp trên Facebook/Instagram app thật, Chrome Android, Safari iPhone và Edge. Kiểm tra keyboard, scroll, back, viewport360/390/430. Ghi thiết bị/OS/app/version thật.

Chỉ ghi PASS khi có bằng chứng Events Manager thật, receipt khớp và không đếm đôi. Fixture/local SDK queue PASS chưa hoàn thành checklist này.

## KPI nội bộ

Chạy bằng DB owner trong SQL Editor; không mở views cho anon/authenticated:

```sql
select * from private.free_registration_funnel_30d_v2 order by source,campaign;

-- Số event thực, dùng khi cần phân biệt nhiều event với session chuyển đổi.
select event_name,count(*) events,count(distinct session_hash) sessions
from private.conversion_funnel_events
where schema_version=2 and occurred_at>=now()-interval '30 days'
group by event_name order by event_name;

-- Tài khoản mới được Auth chấp nhận, và xác minh email tách riêng.
select count(*) filter(where accepted_at is not null) accepted_accounts,
       count(*) filter(where accepted_at is not null and verified_at is not null) verified_accounts
from private.registration_conversion_receipts where created_at>=now()-interval '30 days';

-- Browser retention diagnostic; chưa phải cohort retention theo người dùng.
select event_name,count(*) from private.conversion_funnel_events
where schema_version=2 and event_name in ('free_activation','meaningful_return_d1','meaningful_return_d7')
group by event_name;
```

View30 ngày: `landing_views`, CTA clicks, signup starts và registrations là số **session** chạm bước; `ai_questions`/`ai_results` là tổng event. Tỷ lệ dùng session, chỉ tính cặp bước đúng thứ tự thời gian: Landing→AI; AI result thành công→CTA; CTA→Signup start; Signup start→Complete. Mẫu số0 trả null, không tạo tỷ lệ giả. Campaign/source là first-touch; last-touch vẫn lưu để phân tích riêng. Nhiều tài khoản trong một browser session chỉ tăng một session chuyển đổi, nhưng query accepted_accounts vẫn đếm đủ tài khoản.

Chưa đủ tuổi cohort D1/D7 và chưa có traffic V2 đo thật để kết luận conversion rate. Bản ghi HTTP QA có UUID riêng đã được xóa; SQL fixtures rollback; browser fixtures chặn các request thật. Không đưa các lần QA vào báo cáo hiệu quả Ads.

## Kiểm thử lặp lại

`node --test engine/tests/*.test.mjs` kiểm tra backend receipt, alias/dedupe, privacy, bot và trạng thái model. Sau production build và HTTP server cục bộ, chạy `node scripts/conversion_funnel_qa.cjs`; cần `npx playwright install chromium webkit` (CI thêm `--with-deps`). Windows dùng Edge cài sẵn và WebKit; Facebook/Instagram/Android là viewport/UA emulation, không phải app thật. `supabase/tests/free_registration_funnel.sql` kiểm tra receipt, verified marker, unique event, quyền truy cập và activation từ payment verified trong transaction rollback.
