# V7 × MXH Publish Integration

Mục tiêu: biến V7 thành bảng điều khiển mỏng cho MXH publishing, **không nhúng nguyên MXH Video Tools** và không phụ thuộc UIA để đăng bài.

## Kiến trúc

```
ChatGPT
  → V7 Fast Control / semantic host
  → MXH_V1 structured bridge
  → localhost Automation Hub :4310
  → videoPublish / video_publish_bridge
  → provider/native receipt
```

## Nguyên tắc

- Host cố định duy nhất: `http://127.0.0.1:4310`.
- Không nhận URL tùy ý, shell, executable hoặc code từ caller.
- Video được lấy từ `GET /api/mxh-video-tools/edited-videos`.
- Plan được tạo/reuse qua `POST /api/video-publish/plans`.
- Native scheduling qua `POST /api/jobs` + workflow `video.native_schedule`.
- Trước mutation lấy CSRF từ `GET /api/dashboard/csrf`.
- Identity chuẩn vẫn là `edited_video_sha256 + flow_id`.
- Không retry mù khi kết quả UNKNOWN.
- Không gọi lại nền tảng đã có `scheduleVerified=true`.
- Luồng 1 phải dựa trên Luồng 2 đã có bằng chứng và cách tối thiểu 2 ngày.
- Giữ nguyên title/caption đã khóa; không suy từ tên file kỹ thuật.

## V1 actions

`MXH_V1:<json>`

- `status`
- `list_edited`
- `resolve_title`
- `content_readback`
- `plan_readback`
- `create_or_reuse_plan`
- `native_schedule`
- `job_readback`

Read actions = READ risk. Plan/schedule = MODIFY risk.

## UI panel

Panel V7 tối thiểu:
- video selector từ edited catalog
- exact title readback
- Flow 1 / Flow 2
- platforms
- ngày/giờ 09:00
- **Tạo / dùng plan**
- **Đặt lịch native**
- **Làm mới receipt**
- trạng thái từng nền tảng

Giai đoạn V1 không tự đoán contract "publish now". Nút này chỉ được bật sau khi workflow input hiện hành được xác minh hoặc Hub có route publish-now riêng được contract-test.

## Deploy

Không patch runtime trực tiếp. Source patch phải:
1. khớp expected SHA/anchor;
2. build candidate riêng;
3. chạy unit/regression;
4. cài qua trusted updater/full version candidate;
5. health PASS;
6. rollback nếu health fail.
