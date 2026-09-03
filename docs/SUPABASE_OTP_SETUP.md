# StockRadar — Email OTP 6 số

StockRadar dùng Supabase Auth cho email + mật khẩu và xác minh email bằng OTP 6 số.

## Luồng người dùng

1. Người dùng nhập email + mật khẩu.
2. Supabase tạo tài khoản ở trạng thái chờ xác minh.
3. Email xác minh gửi mã `{{ .Token }}` gồm 6 chữ số.
4. Người dùng nhập mã tại `/signup/`.
5. Frontend gọi `supabase.auth.verifyOtp({ email, token, type: 'email' })`.
6. Khi xác minh thành công, Supabase tạo session và StockRadar chuyển sang `/tai-khoan/`.

Frontend không lưu mật khẩu. Email chờ xác minh chỉ được giữ tạm trong `sessionStorage` để người dùng có thể reload trang mà không phải nhập lại email.

## Cấu hình bắt buộc trong Supabase Dashboard

Vào **Authentication → Email Templates → Confirm signup** và thay nội dung bằng mẫu có `{{ .Token }}`. Có thể giữ cả mã OTP và nút xác minh để có phương án dự phòng.

```html
<h2>Xác minh tài khoản StockRadar</h2>
<p>Mã xác minh của bạn:</p>
<p style="font-size:32px;font-weight:700;letter-spacing:8px">{{ .Token }}</p>
<p>Nhập mã 6 số này tại trang đăng ký StockRadar.</p>
<p>Nếu cần, bạn cũng có thể xác minh bằng liên kết dưới đây:</p>
<p><a href="{{ .ConfirmationURL }}">Xác minh email</a></p>
```

Không gửi OTP tài khoản môi giới, OTP ngân hàng hoặc mã giao dịch vào StockRadar. OTP ở đây chỉ dùng để xác minh tài khoản website StockRadar.

## Gửi lại mã

Frontend dùng:

```js
supabase.auth.resend({
  type: 'signup',
  email,
  options: { emailRedirectTo: '<STOCKRADAR_ACCOUNT_URL>' }
})
```

UI có cooldown phía client; Supabase tiếp tục áp dụng rate limit phía server.
