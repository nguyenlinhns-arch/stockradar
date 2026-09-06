# Production Product Audit — 06/09/2026

**TESTING / BLOCKED — chưa hoàn tất production, chưa đủ điều kiện chạy Ads.** Audit này thay thế kết luận vận hành ngày 05/09 và các bảng lịch sử BUILD_STATUS. Không redesign; AI là trung tâm, HOSE-only, không dữ liệu hoặc giao dịch giả trên production.

Baseline `969d88ba8360144958f4945f0958f9f100544210`; Pages [33998348779](https://github.com/nguyenlinhns-arch/stockradar/actions/runs/33998348779) SUCCESS. Bằng chứng release mới ở cuối tài liệu.

## Đợt Facebook → AI → Free, tiếp tục từ production hiện tại

**DONE code / TESTING đo lường production / BLOCKED mở Ads.** Baseline lúc bắt đầu `e494f84`; đã fast-forward commit `2f1ac78` trên main để giữ migration `decouple_ai_only_synthesis_from_research_grade`. Không khôi phục nhãn health cũ: hiện `AI_ONLY_REFERENCE_READY`, 405 reference/0 Research-Grade; đây là coverage dữ liệu, không phải model E2E PASS.

| Hạng mục | Trạng thái | Bằng chứng / giới hạn |
|---|---|---|
| Guest → Free | DONE | CTA dưới kết quả MODEL_READY đầu tiên; khóa impression qua reload, nhắc còn1/hết lượt; không hiện cho Free/Premium; URL `signup/?plan=free` |
| Free-first signup | DONE | Ẩn chọn Premium/email Premium; email + hai ô mật khẩu + legal consent; honeypot ẩn; không thanh toán hay tự cấp quyền |
| Verification/session | DONE code, TESTING app thật | Public Auth signUp vẫn bắt verification; hướng dẫn sau submit; callback SDK về Home, thiếu session/verifier về login; fixture kiểm quota10, reload, back/forward và hỏi tiếp |
| Meta | DONE integration / BLOCKED production | Cấu hình tập trung, SDK async/optional; PageView, AIQuestion, StartRegistration, CompleteRegistration có eventID. **META_PIXEL_ID_NOT_CONFIGURED; Events Manager chưa kiểm chứng** |
| Registration authority | DONE | Auth INSERT receipt + flow matching, unique event; browser không thể chèn completion vào DB. SQL rollback kiểm new/existing flow, retry, verified marker, ACL, metadata; backend fixture phân biệt Auth acceptance và receipt |
| CAPI | CAPI_NOT_CONFIGURED | Receipt/event_id ổn định là interface cho sender tương lai; chưa có server CAPI, không token công khai |
| Attribution/KPI | DONE code / TESTING dữ liệu thật | First/last touch30 ngày, UTM5 + fbclid; canonical aliases dùng chung dedupe. Hai private SQL views30 ngày + query event/account/verified. Không có số conversion/retention thật để kết luận |
| Model observability | DONE / BLOCKED provider | `stock-ai` v24, `stock-ai-guest` v23. HTTP thật trả200 `READY_FALLBACK`, `OPENAI_429_CREDIT_BALANCE_EXHAUSTED`, `MODEL_CREDIT_BLOCKED`, quota Guest còn2/3. Fallback/METHOD_ONLY không tăng ai_result_success |
| Data/hero copy | DONE | Input AI nằm first screen traffic Facebook; trạng thái tham chiếu/intraday chưa khả dụng bằng tiếng Việt, giữ fail-closed; claim email chỉ đổi khi readiness thật cho phép |
| Mobile/UA/engines | DONE emulation / TESTING thiết bị thật |360/390/430; Facebook Android UA, Instagram iPhone UA, Chrome Android UA, WebKit iPhone viewport và Edge desktop thật qua browser fixture. Không tuyên bố app Facebook/Instagram hoặc bàn phím điện thoại thật đã PASS |

`signup-link` v4 và `conversion-event` v4 ACTIVE; migration canonical funnel đã apply. HTTP thật của conversion-event: lần đầu202/recorded=true, lặp UUID202/false, bot202/false, forged signup_completed400. Bản ghi QA có UUID riêng đã xóa; không tạo tài khoản/email production trong đợt funnel. SQL fixtures rollback, dispatch chỉ tắt trong transaction thử và không ảnh hưởng cấu hình bên ngoài.

Regression:463 unittest PASS;465 pytest +28 subtests PASS (Windows dùng basetemp riêng vì temp hệ thống bị ACL);75 Node tests PASS; production build/SEO/asset guards PASS;85/85 visual checks; auth-session, signup-verification, product-decision8, radar-session và conversion browser14 scenarios PASS. SQL5 scripts PASS, gồm server-only Premium activation từ verified grant. Test reference_health được cập nhật để chấp nhận nhãn reference-only mới nhưng vẫn kiểm grade0, future timestamps/dates, stale data và ACL. Browser fixture chờ request hoàn tất trước các lần reload lập trình để tránh hủy request đang bay trong WebKit.

Budget byte giữ nguyên: Home151547/196000 bytes, signup261255/275000, login238196/245000, checkout215085/230000 trước cleanup cuối. Login thêm analytics runtime (12 JS); Terser chỉ dùng lúc build để giảm dung lượng, không thêm runtime dependency. Privacy kiểm metadata tối thiểu, không prompt/email/holdings/token; Pixel có opt-out và bỏ URL/referrer nhạy cảm. Bot filter là UA/honeypot/rate-limit, không phải chứng minh mọi traffic đều là người.

Advisors:0 ERROR; các WARN hiện có về RPC có chủ đích và HIBP còn. Receipt mới private/RLS, không cấp anon/authenticated; INFO không có policy phù hợp với bảng chỉ server truy cập. [Giải thích RLS lint](https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy), [HIBP](https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection).

Blocker để mở Ads: Pixel ID + CompleteRegistration thật đúng một lần trong Events Manager; OpenAI credit; SMTP Auth và email ngoài team; kiểm thử app/thiết bị thật. Action/data rights/compliance/email sản phẩm/checkout vẫn theo gate PAUSED. Không coi cảnh báo này là đã giải quyết. Cấu hình, event definitions, KPI SQL, privacy và checklist ở [META_ADS_MEASUREMENT.md](META_ADS_MEASUREMENT.md).

CI đầu tiên [34012730997](https://github.com/nguyenlinhns-arch/stockradar/actions/runs/34012730997) dừng đúng tại lỗi WebKit khi listener tài khoản/thông báo bắt đầu request trong lúc login chuyển trang. Đã thêm trạng thái chuyển trang để hoãn các request này; lỗi đăng nhập hoặc quay lại trang qua browser cache sẽ bỏ trạng thái chờ. Không bỏ kiểm thử pageerror, không bỏ WebKit. Frontend release `0ce0b555161100103f89d027c36fdea6807c9702`: [Pages34013045603 SUCCESS](https://github.com/nguyenlinhns-arch/stockradar/actions/runs/34013045603), hoàn tất05:07:36 UTC ngày06/09. Cả build và deploy PASS; toàn bộ browser tests, gồm WebKit và14 funnel scenarios, đã qua trên CI. Production12/12 routes HTTP200,10/10 JS assets khớp build sau chuẩn hóa xuống dòng; Home canonical/index và auth/signup/checkout noindex đúng. Browser production390px: input AI ở y472.625px, không overflow; Free form ẩn Premium/options/honeypot đúng. Pixel production xác nhận vẫn chưa cấu hình. Secret scan635 tracked files/2384 reachable history blobs,0 findings sau code commit. Không còn receipt hoặc event QA thử nghiệm; product_ready/checkout_ready vẫn false. Các release bên dưới là lịch sử.

## P0/P1/P2

| Ưu tiên | Hạng mục | Trạng thái | Kết quả / giới hạn |
|---|---|---|---|
| P0 | Collect → Research → bundle → cache → orchestrator | DONE code + lượt EOD thật / BLOCKED intraday | Collector và chuỗi Research→bundle→sync→orchestrator SUCCESS; 405 reference được nhập, research cũ được dọn về0 đúng grade. Đóng gói đúng fundamentals, concurrency, main/repo/artifact guards, mask và kiểm chữ ký/claims OIDC. |
| P0 | Scanner 4 mốc | DONE code / BLOCKED phiên thật | SLA V2 kiểm từng mã thanh khoản: nến và quote cùng phiên, tuổi ≤20 phút, đúng checkpoint và trễ ≤20 phút. EOD/manual/cuối tuần không chứng minh intraday. Giữ artifact lỗi và danh sách mã stale. |
| P0 | Pocket Pivot / volume / giá | DONE code | Không dùng EOD/phiên trước làm volume hiện tại hoặc volume dự phóng làm PP xác nhận; max down-volume đúng 10 phiên trước; same-time/progress cần ≥10 mẫu. Loại nến future/trùng/sai OHLCV, daily chưa hoàn tất; quote thiếu/sai gắn EOD_REFERENCE; pivot gồm phiên hoàn tất gần nhất. |
| P0 | Full HOSE AI | DONE lookup reference / BLOCKED model + research | 09:04 VN:405 reference fresh theo TTL,0 research-ready,0 ngoài HOSE, một snapshot mới. Giá nguồn04/09 vẫn là EOD; không mượn volume cũ để nâng grade. OpenAI trả CREDIT_BALANCE_EXHAUSTED; fallback không phải model E2E PASS. |
| P0 | Decision / Action | BLOCKED | API disabled, không active manifest/snapshot, data-rights/compliance false. Không xuất target/Buy Zone khi thiếu dữ liệu; score không phải probability. |
| P0 | Free signup / session / quota | DONE sửa + QA thật / TESTING quy mô | Bỏ admin.createUser(email_confirm:true); public Auth signUp bắt buộc mailer_autoconfirm=false, trả202 chờ xác minh. Guest3/Free10 ngày VN/Premium unlimited ngày, burst30/phút. |
| P0 | Email admin Free | DONE runtime có kiểm soát | Một signup QA thật: Resend SENT attempts1, Gmail Inbox từ alerts@stockradar.vn, webhook email.sent + email.delivered. Sửa claim SQL ambiguous email_kind/expires_at và claim timeout lần cuối; không cấp Premium/consent Premium. |
| P0 | Email payment / xác nhận cuối | DONE code / BLOCKED giao dịch thật | HMAC token ổn định, expiry đóng băng khi retry, provider idempotency, timeout/retry hữu hạn; retry cron cho request USER_CONFIRMED thật. GET chỉ xem, POST cuối resolve; bấm lặp không cấp/gửi lại. Production checkout_count=0. |
| P0 | Premium Daily09:00 / Action Alert | BLOCKED | Provider/domain/unsubscribe/bounce có approval và delivery thật admin; compliance thiếu. Product sending/scheduler=false; không gửi thử bằng tín hiệu giả. |
| P0 | Checkout 199.000đ/30 ngày | BLOCKED | PAUSED; billing/product/email/checkout=false. Không tự gia hạn, không tự xác minh ngân hàng, frontend không tự cấp quyền. |
| P1 | Mobile / Home / SEO | DONE QA / TESTING chính sách public | 17 trang ×360/390/430/768/1440 =85 checks. Canonical stockradar.vn; bản build hiện index7 route public gồm Home/radar5/kiểm tra cổ phiếu/khuyến nghị/ngành/hiệu quả/đăng ký landing. Login/signup/account/checkout và thin ticker noindex. Home đã indexable; không có boolean compliance riêng cho SEO. /kien-thuc/ đã bị build legacy loại khỏi sitemap và không xuất bản, không tính là route PASS. Chưa xác nhận pháp lý cho public marketing. |
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
- Đã xóa chính tài khoản QA bằng endpoint delete-account sau đăng nhập lại:200; login sau xóa bị từ chối và DB còn0 QA user. Token đã logout bị401, không dùng kết quả này để tuyên bố negative test recent-session403. Gate recent-session được kiểm trong SQL rollback. Không tạo payment request hoặc chuyển khoản giả.
- HIBP: dashboard ghi chỉ Pro trở lên, dự án Free; không tự mua nâng gói. [Supabase password security](https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection).

## Kiểm thử trước release

| Kiểm thử | Kết quả |
|---|---|
| python -m unittest discover -s engine/tests -v | 463 PASS |
| python -m pytest engine/tests -q | 465 PASS +28 subtests; gồm hai function tests unittest không discover |
| node --test engine/tests/*.test.mjs | 66 PASS, gồm auth/payment handlers và RSA OIDC signatures với issuer fixture |
| python scripts/build_production.py | PASS artifact guards |
| npm run visual-qa | 85/85 PASS |
| auth_session_qa.cjs | Free/Paid login→Home→reload→AI→Radar→Home→logout; server tier đổiPAID cập nhật header không login lại PASS (HTTP fixture) |
| signup_verification_qa.cjs | Free/Premium mobile chờ xác minh, xóa password, không auto-login/checkout/grant PASS (HTTP fixture) |
| product_decision_qa.cjs / radar_session_qa.cjs | PASS decision/stale/XSS/privacy/checkout closed ở5 viewport; Radar3 viewport + session |
| supabase/tests/*.sql | 4 scripts PASS trên project thật trong transaction rollback. Ba script auth/payment/email tắt transactional dispatch trong transaction; reference_health.sql kiểm nhãn reference-only, ACL, future timestamp/date và source date cũ. Không fixture sót/gửi email |

SQL chứng minh quota3/10/unlimited, burst30, cấm self-grant, expiry/future/mock/non-HOSE/manifest/privacy/weekend/dedup/consent. Fixture payment→admin/approval, Daily/Action preflight và Premium refresh chỉ chứng minh kỹ thuật; không thay thế tiền thật, thư sản phẩm hoặc phiên intraday. Hai test cũ yêu cầu auto-confirm được đổi sang cấm bypass/bắt public Auth; không bỏ test làm xanh build.

## Runtime / observability 09:04 VN

Health RPC báo REFERENCE_ONLY_RESEARCH_BLOCKED; coverage405/405 fresh theo TTL, research0. Snapshot2026-09-06T01:56:51Z; dữ liệu giá vẫn04/09. Nhãn cũ từng báo RESEARCH_READY dù research0 đã sửa; generated_at tương lai hoặc source date quá cũ không được tính fresh. Product readiness PAUSED, bốn readiness false. Email approval RPC có các chứng cứ provider/domain/unsubscribe/bounce nhưng ready_to_activate=false, ready_to_send_now=false, COMPLIANCE_APPROVAL_MISSING; delivery gate chưa được kích hoạt.

Sau cleanup QA: outbox0 SENT/0 FAILED/0 PROCESSING/1 PENDING welcome cũ; row SENT của QA đã cascade khi xóa account. Bằng chứng giao thư vẫn còn trong Gmail và hai webhook events (sent/delivered). Checkout0, QA user0 và fixture example.invalid0. Private tables và credential không đưa lên Pages.

Vận hành: Actions run/job logs tìm bước fail; SLA artifact tìm ticker/source stale; private.email_outbox status/attempts/last_error/expiry + private.email_delivery_events phân biệt gửi/giao; private.checkout_requests và private.checkout_approvals tìm pending/expiry/retry; suppression giữ reason.

Advisors28 INFO (private RLS deny by absence of policy),11 WARN:10 SECURITY DEFINER grants có chủ đích cho readiness/own-user RPC,1 HIBP thiếu do gói. Không thu hồi RPC máy móc; giữ kiểm ACL/gate. [Anon linter](https://supabase.com/docs/guides/database/database-linter?lint=0028_anon_security_definer_function_executable), [authenticated linter](https://supabase.com/docs/guides/database/database-linter?lint=0029_authenticated_security_definer_function_executable).

Edge đã deploy: signup-link3, checkout-approval3, free-signup-admin-notify2, email-webhook6, stock-research-sync5, stock-alert-orchestrator2. Ba migration mới đã apply qua connector: harden_transactional_approval_delivery, fix_admin_signup_outbox_claim, truthful_reference_health_status; không push lại lịch sử remote timestamp khác local.

OIDC dùng workflow_ref theo [GitHub claims](https://github.blog/changelog/2023-01-10-github-actions-openid-connect-token-now-supports-more-claims-for-configuring-granular-cloud-access/), job_workflow_ref mô tả [reusable workflow](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-with-reusable-workflows). Provider retry tuân [Resend idempotency](https://resend.com/docs/dashboard/emails/idempotency-keys).

## Điều kiện còn thiếu

1. Nguồn/master/rights + snapshot Decision-Grade đối chiếu, compliance approval thật; dùng runbook05/09, không bỏ validation bằng boolean trực tiếp.
2. OpenAI API credit hết; cần xử lý billing và kiểm tra lại model qua endpoint hiện có. SMTP auth production cho mailbox ngoài team chưa cấu hình; HIBP cần gói hỗ trợ.
3. Đối chiếu10:30/11:15/13:30/14:15 một phiên HOSE thật; cron/fixture không phải PASS vận hành.
4. Sau gate hợp lệ: chuyển khoản thật có đối soát, admin xác nhận cuối, cấp đúng30 ngày/email receipt; Daily09:00 và Action với signal thật đủ chuẩn.
5. Restore drill, cohortD1/D7, lịch sử LIVE_PUBLISHED đủ mẫu.

## Xác minh sau release

Mã frontend/pipeline cuối: [19a2825df053f9fd288d360b05e5c28a1d3cd078](https://github.com/nguyenlinhns-arch/stockradar/commit/19a2825df053f9fd288d360b05e5c28a1d3cd078), đã push main. [Pages34005145039](https://github.com/nguyenlinhns-arch/stockradar/actions/runs/34005145039) build và deploy SUCCESS. Commit kết sổ chỉ thay audit/build status, migration health đã apply và SQL regression; không đổi artifact frontend của release này.

Chuỗi dùng collector thật nêu dưới, [Research34005145048](https://github.com/nguyenlinhns-arch/stockradar/actions/runs/34005145048) → [bundle34005185230](https://github.com/nguyenlinhns-arch/stockradar/actions/runs/34005185230) → [sync34005198194](https://github.com/nguyenlinhns-arch/stockradar/actions/runs/34005198194) → [orchestrator34005220581](https://github.com/nguyenlinhns-arch/stockradar/actions/runs/34005220581) đều SUCCESS. Runtime xác nhận405 reference mới, research0; orchestrator thành công với gate đóng, không đồng nghĩa gửi Action thành công.

Production smoke sau deploy:12/12 route HTTP200 (Home, signup, login, account, checkout, reset password, Radar, khuyến nghị, hiệu quả, kiểm tra cổ phiếu, điều khoản, quyền riêng tư). 7/7 JS asset khớp nội dung build sau chuẩn hóa CRLF/LF; không tuyên bố raw hash giống nhau giữa Windows/Linux. Mobile fixture và production auth session được phân biệt trong bảng test. Secret scan kết sổ được ghi ở BUILD_STATUS.

### Phát hiện runtime sau Pages release 4d165c7

- Pages [34004657025](https://github.com/nguyenlinhns-arch/stockradar/actions/runs/34004657025): build/deploy SUCCESS; asset signup thực chứa verification_required. Browser production QA thật: login→Home→reload→HPG AI→Radar→Home→logout PASS, Free10→9 giữ qua reload/đổi trang; Radar RPC405 items,0 ngoài HOSE. Một probe chẩn đoán tiếp theo dùng thêm1 lượt (còn8).
- **OpenAI model BLOCKED:** response READY_FALLBACK, reason OPENAI_429_CREDIT_BALANCE_EXHAUSTED. STOCKRADAR_CORE/RESEARCH_ONLY trả nội dung dự phòng; không coi đây là model E2E PASS. Cần chủ tài khoản xử lý [API billing](https://platform.openai.com/settings/organization/billing); không tự nạp tiền/đổi key. [Error-code guidance](https://developers.openai.com/api/docs/guides/error-codes).
- Backend Require current password when updating đã bật và lưu. API thật với QA từ chối request thiếu mật khẩu hiện tại:400 current_password_required. Thư recovery thật đã nhận; redirect_to đúng https://stockradar.vn/dat-lai-mat-khau/. Không đổi mật khẩu thật của chủ dự án.
- Collector [34004657032](https://github.com/nguyenlinhns-arch/stockradar/actions/runs/34004657032) SUCCESS:405 master,394 full_scan_eligible,110 thanh khoản≥500k,405 WATCH; SLA EOD_RESEARCH/internal_research_ready=true/internal_scan_ready=false/public_action_allowed=false. Đây là kiểm chứng đóng đúng cổng cuối tuần, không phải4 mốc intraday PASS.
- Research [34004885755](https://github.com/nguyenlinhns-arch/stockradar/actions/runs/34004885755) SUCCESS nhưng bundle [34004932067](https://github.com/nguyenlinhns-arch/stockradar/actions/runs/34004932067) bị legacy validator từ chối vì0 INTERNAL_RESEARCH_READY. Không khôi phục volume phiên cũ để nâng grade. Sửa riêng chế độ --dry-run --full-reference: bắt đủ405 ticker duy nhất, identity từng row, boolean grade/count khớp và mọi public/alpha gate false. Legacy research-only writer vẫn từ chối0 research; Edge sync vốn hỗ trợ405 reference + prune research cũ về0 sau import thành công. Ba regression mới chứng minh incomplete/overclaimed/identity/action/alpha sai đều bị chặn.
