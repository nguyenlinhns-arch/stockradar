# Production Product Audit — 06/09/2026

**TESTING / BLOCKED — chưa hoàn tất production, chưa đủ điều kiện chạy Ads.** Audit này thay thế kết luận vận hành ngày 05/09 và các bảng lịch sử BUILD_STATUS. Không redesign; AI là trung tâm, HOSE-only, không dữ liệu hoặc giao dịch giả trên production.

Baseline `969d88ba8360144958f4945f0958f9f100544210`; Pages [33998348779](https://github.com/nguyenlinhns-arch/stockradar/actions/runs/33998348779) SUCCESS. Bằng chứng release mới ở cuối tài liệu.

## P0/P1/P2

| Ưu tiên | Hạng mục | Trạng thái | Kết quả / giới hạn |
|---|---|---|---|
| P0 | Collect → Research → bundle → cache → orchestrator | DONE code / TESTING runtime | Đóng gói đúng fundamentals scanner đã sử dụng trong lượt intraday; concurrency collector; workflow_run và artifact chỉ nhận main cùng repo; mask OIDC; verifier kiểm workflow_ref đúng loại workflow, giữ chữ ký/issuer/audience/repo/ref/time và job_workflow_ref nếu có. |
| P0 | Scanner 4 mốc | DONE code / BLOCKED phiên thật | SLA V2 kiểm từng mã thanh khoản: nến và quote cùng phiên, tuổi ≤20 phút, đúng checkpoint và trễ ≤20 phút. EOD/manual/cuối tuần không chứng minh intraday. Giữ artifact lỗi và danh sách mã stale. |
| P0 | Pocket Pivot / volume / giá | DONE code | Không dùng EOD/phiên trước làm volume hiện tại hoặc volume dự phóng làm PP xác nhận; max down-volume đúng 10 phiên trước; same-time/progress cần ≥10 mẫu. Loại nến future/trùng/sai OHLCV, daily chưa hoàn tất; quote thiếu/sai gắn EOD_REFERENCE; pivot gồm phiên hoàn tất gần nhất. |
| P0 | Full HOSE AI | TESTING | 08:38 VN: 405 reference fresh theo TTL, 105 research-ready, 300 reference-only, 0 ngoài HOSE, một snapshot. Giá nguồn 04/09; generated_at 05/09 không biến giá thành intraday 06/09. Không coi mọi mã là Decision-Grade. |
| P0 | Decision / Action | BLOCKED | API disabled, không active manifest/snapshot, data-rights/compliance false. Không xuất target/Buy Zone khi thiếu dữ liệu; score không phải probability. |
| P0 | Free signup / session / quota | DONE sửa + QA thật / TESTING quy mô | Bỏ admin.createUser(email_confirm:true); public Auth signUp bắt buộc mailer_autoconfirm=false, trả202 chờ xác minh. Guest3/Free10 ngày VN/Premium unlimited ngày, burst30/phút. |
| P0 | Email admin Free | DONE runtime có kiểm soát | Một signup QA thật: Resend SENT attempts1, Gmail Inbox từ alerts@stockradar.vn, webhook email.sent + email.delivered. Sửa claim SQL ambiguous email_kind/expires_at và claim timeout lần cuối; không cấp Premium/consent Premium. |
| P0 | Email payment / xác nhận cuối | DONE code / BLOCKED giao dịch thật | HMAC token ổn định, expiry đóng băng khi retry, provider idempotency, timeout/retry hữu hạn; retry cron cho request USER_CONFIRMED thật. GET chỉ xem, POST cuối resolve; bấm lặp không cấp/gửi lại. Production checkout_count=0. |
| P0 | Premium Daily09:00 / Action Alert | BLOCKED | Provider/domain/unsubscribe/bounce có approval và delivery thật admin; compliance thiếu. Product sending/scheduler=false; không gửi thử bằng tín hiệu giả. |
| P0 | Checkout 199.000đ/30 ngày | BLOCKED | PAUSED; billing/product/email/checkout=false. Không tự gia hạn, không tự xác minh ngân hàng, frontend không tự cấp quyền. |
| P1 | Mobile / Home / SEO | DONE QA / TESTING production | 17 trang ×360/390/430/768/1440 =85 checks. Giữ AI/Home; canonical stockradar.vn; 7 route kiến thức/landing index; Home chịu compliance gate; auth/account/checkout/thin ticker noindex. |
| P1 | Analytics | DONE code / TESTING đo lường | Landing/AI/result/intent/checkout; thêm signup_verification_requested và payment_submitted sau response hợp lệ. Auth creation/verification, approval/grant và delivery lấy từ server audit; không tin browser cho doanh thu. D1/D7 cần cohort thật. |
| P1 | Track record | DONE gate / BLOCKED mẫu thật | Chỉ LIVE_PUBLISHED/DECISION_GRADE; không tạo số đẹp hoặc bỏ lệnh thua. Chưa đủ mẫu giữ CHƯA ĐỦ MẪU. |
| P1 | Security | DONE rà / BLOCKED HIBP | Secret scan, ACL/RLS tests; approval no-store/no-referrer/noindex/CSP/frame deny; webhook kiểm độ dài body thực. Advisors0 ERROR/11 WARN, không báo sạch hoàn toàn. |
| P2 | Restore / retention / một phiên | BLOCKED | Chưa backup restore drill, đủ thời gian D1/D7 hoặc bốn mốc phiên thật. |

## Dữ liệu và engine

Đã đọc đủ 10 tài liệu yêu cầu, workflows, migrations, Edge Functions auth/AI/API/email/checkout và runtime Supabase. Giữ chuỗi 4M/Payback → CANSLIM/valuation → SEPA/VCP → VPA/PP → Ichimoku/Bollinger → market → decision.

Master405 vẫn là invariant của universe hiện hành; trạng thái listing/tradable và master được phê duyệt chưa chứng minh đầy đủ. Raw OHLCV/fundamentals/events/sector/valuation/market context đi qua pipeline nội bộ/data-layer. Corporate actions/disclosures authoritative, rights từng nguồn, coverage theo mã và manifest publication vẫn có thể chặn Decision-Grade. AI_ONLY không đồng nghĩa quyền public raw hoặc Action; nguồn cấm derived/third-party vẫn bị chặn.

## Auth/email thật

- Tạo đúng một tài khoản QA trong mailbox chủ dự án kiểm soát. Password/session chỉ ở private-staging bị gitignore; không ghi vào audit/public artifact.
- Trước xác minh: FREE/PENDING, login bị email_not_confirmed. Sau mở link thật: FREE/ACTIVE, login có session. Không bật Daily/Action Premium.
- Phát hiện Site URL localhost:3000; đã lưu https://stockradar.vn/ và allowlist exact Home, /thanh-toan/?plan=premium, /dat-lai-mat-khau/ trên dashboard.
- Email xác minh hiện từ Supabase Auth mặc định. **Custom SMTP auth cho người dùng công cộng chưa xác minh/cấu hình**; gửi tới mailbox chủ dự án chưa chứng minh gửi cho mọi người. Cần SMTP production + mailbox ngoài team trước mở rộng.
- Backend OTP length8; UI nhận6–8 chữ số và hướng dẫn mở link khi thư có link; không cắt mã8 còn6. Backend kiểm tính hợp lệ; resend/verify quay về Home.
- Admin signup: Gmail nhận08:25 VN; Resend outbox SENT và webhook sent/delivered thật. Cron succeeded/pending không được coi là giao thư.
- HIBP: dashboard ghi chỉ Pro trở lên, dự án Free; không tự mua nâng gói. [Supabase password security](https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection).

## Kiểm thử trước release

| Kiểm thử | Kết quả |
|---|---|
| python -m unittest discover -s engine/tests -v | 460 PASS |
| python -m pytest engine/tests -q | 462 PASS +22 subtests; gồm hai function tests unittest không discover |
| node --test engine/tests/*.test.mjs | 66 PASS, gồm auth/payment handlers và RSA OIDC signatures với issuer fixture |
| python scripts/build_production.py | PASS artifact guards |
| npm run visual-qa | 85/85 PASS |
| auth_session_qa.cjs | Free/Paid login→Home→reload→AI→Radar→Home→logout; server tier đổiPAID cập nhật header không login lại PASS (HTTP fixture) |
| signup_verification_qa.cjs | Free/Premium mobile chờ xác minh, xóa password, không auto-login/checkout/grant PASS (HTTP fixture) |
| product_decision_qa.cjs / radar_session_qa.cjs | PASS decision/stale/XSS/privacy/checkout closed ở5 viewport; Radar3 viewport + session |
| supabase/tests/*.sql | 3 scripts PASS trên project thật trong transaction rollback, transactional dispatch disabled trong transaction, không fixture sót/gửi email |

SQL chứng minh quota3/10/unlimited, burst30, cấm self-grant, expiry/future/mock/non-HOSE/manifest/privacy/weekend/dedup/consent. Fixture payment→admin/approval, Daily/Action preflight và Premium refresh chỉ chứng minh kỹ thuật; không thay thế tiền thật, thư sản phẩm hoặc phiên intraday. Hai test cũ yêu cầu auto-confirm được đổi sang cấm bypass/bắt public Auth; không bỏ test làm xanh build.

## Runtime / observability 08:38 VN

Health RPC báo AI_ONLY_READY cho research, không phải toàn sản phẩm READY. Product readiness PAUSED, bốn readiness false. Email RPC status READY nhưng ready_to_activate=false, ready_to_send_now=false, COMPLIANCE_APPROVAL_MISSING.

Outbox1 SENT admin/0 FAILED/0 PROCESSING/2 PENDING welcome;1 sent+1 delivered webhook. Checkout0. Fixture domain example.invalid còn0. Private tables và credential không đưa lên Pages.

Vận hành: Actions run/job logs tìm bước fail; SLA artifact tìm ticker/source stale; private.email_outbox status/attempts/last_error/expiry + private.email_delivery_events phân biệt gửi/giao; private.checkout_requests và private.checkout_approvals tìm pending/expiry/retry; suppression giữ reason.

Advisors28 INFO (private RLS deny by absence of policy),11 WARN:10 SECURITY DEFINER grants có chủ đích cho readiness/own-user RPC,1 HIBP thiếu do gói. Không thu hồi RPC máy móc; giữ kiểm ACL/gate. [Anon linter](https://supabase.com/docs/guides/database/database-linter?lint=0028_anon_security_definer_function_executable), [authenticated linter](https://supabase.com/docs/guides/database/database-linter?lint=0029_authenticated_security_definer_function_executable).

Edge đã deploy: signup-link3, checkout-approval3, free-signup-admin-notify2, email-webhook6, stock-research-sync5, stock-alert-orchestrator2. Hai migration mới apply qua connector; không push lại lịch sử remote timestamp khác local.

OIDC dùng workflow_ref theo [GitHub claims](https://github.blog/changelog/2023-01-10-github-actions-openid-connect-token-now-supports-more-claims-for-configuring-granular-cloud-access/), job_workflow_ref mô tả [reusable workflow](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-with-reusable-workflows). Provider retry tuân [Resend idempotency](https://resend.com/docs/dashboard/emails/idempotency-keys).

## Điều kiện còn thiếu

1. Nguồn/master/rights + snapshot Decision-Grade đối chiếu, compliance approval thật; dùng runbook05/09, không bỏ validation bằng boolean trực tiếp.
2. SMTP auth production cho mailbox ngoài team; HIBP cần gói hỗ trợ.
3. Đối chiếu10:30/11:15/13:30/14:15 một phiên HOSE thật; cron/fixture không phải PASS vận hành.
4. Sau gate hợp lệ: chuyển khoản thật có đối soát, admin xác nhận cuối, cấp đúng30 ngày/email receipt; Daily09:00 và Action với signal thật đủ chuẩn.
5. Restore drill, cohortD1/D7, lịch sử LIVE_PUBLISHED đủ mẫu.

## Xác minh sau release

TESTING: bổ sung SHA main, Pages run, pipeline và production smoke sau khi thực sự hoàn tất; không dùng baseline thay bằng chứng release mới.
