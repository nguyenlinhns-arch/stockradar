# Đối chiếu lịch sử khuyến nghị — 05/09/2026

## Kết quả và nguyên nhân

Đã xác minh 3 email cảnh báo, tương ứng 2 mã. DCM: phát hiện 11:17 ngày
03/09/2026, gửi 11:20:16; điều chỉnh lúc 14:15, gửi 14:21:35. VHM: phát hiện
14:15 ngày 04/09/2026, gửi 14:18:48 đến 4 địa chỉ. Giờ Việt Nam.

Thư gốc có nhãn SENT trong Gmail. NHAT_KY_EMAIL ghi nhận VHM, số người nhận 4,
trạng thái SENT. Không suy diễn thành đã giao thành công đến mọi hộp thư.
DCM lần đầu có 1 người nhận, lần điều chỉnh có 2; không gán cả ba lần gửi cho 4 người.
Thư và địa chỉ người nhận giữ riêng trong private-staging, không xuất bản.

Website dùng recommendations.json rỗng và RPC chỉ xét **mua mới ở lần quét hiện tại**.
private.stock_signal_events có 0 dòng; cache nghiên cứu không phải nhật ký phát hành.
Do vậy con số 0 không chứng minh chưa từng gửi khuyến nghị hoặc đã bán DCM/VHM.
Khôi phục bằng luồng lịch sử có bằng chứng độc lập; không sửa điều kiện mua mới,
không giả phê duyệt, không chuyển cảnh báo cũ thành tín hiệu mua hôm nay.

## Sổ đối chiếu

`track-record/verified-email-alerts.json` chứa các sự kiện BUY/UPDATE có mã định danh,
thời điểm phát hiện, thời điểm gửi thật, số người nhận và SHA-256 nội dung text thư.
Không ghi đè khuyến nghị ban đầu bằng lần DCM buổi chiều. Nếu có email bán hoặc
hiệu chỉnh, thêm sự kiện có bằng chứng thay vì viết lại sự kiện cũ.

Giá báo tin đầu DCM 32.200đ, VHM 75.400đ. Đóng cửa 04/09 lần lượt 32.550đ và
75.200đ: biến động giá +1,0870% và −0,2653%. Đây không phải lãi/lỗ khớp lệnh;
không có bằng chứng giao dịch, phí, thuế, cổ tức/quyền. Không tính tỷ lệ thắng hoặc
lãi/lỗ đã chốt. Giá trong email có thể khác mức mua được sau thời điểm gửi.

Đã tìm thư trong khoảng 01/08–05/09 theo DCM/VHM/StockRadar, tiêu đề chứng khoán
và điều kiện bán/cắt lỗ. Thư DCM chiều có từ “bán” nói về MBB/thị trường, không
phải email bán DCM. Bản tin sáng 04/09 chỉ theo dõi MBB/HPG/FPT/ACB/HAH và dẫn
khuyến nghị công ty chứng khoán; không nhập chúng thành khuyến nghị mua StockRadar.
Không tìm thấy email bán DCM/VHM trong phạm vi đã kiểm tra. Phạm vi này có mốc
kết thúc riêng, không tự kéo dài khi giá được cập nhật.

## Rà soát tháng 8

- 31 ngày lịch, 20 phiên quan sát từ 03/08 đến 28/08. 31/08 nghỉ giao dịch theo
  [thông báo của KIS ngày 26/08](https://dxkmmj70ij70u.cloudfront.net/thong-bao-lich-nghi-le-quoc-khanh-02092026).
- Danh sách 405 HOSE hiện tại, không có hồ sơ thành phần sàn tại từng ngày trong quá khứ.
- 292.224 dòng nguồn, không trùng mã/ngày; 30 dòng OHLC không hợp lệ bị loại, không sửa số.
- Mỗi phiên có 365–381 mã có dòng giá; yêu cầu ≥252 dòng hợp lệ để tính MA và lịch sử.
  Mã thiếu dữ liệu không được điền giá cũ và không được xem là đạt.
- 25 lần đạt bước lọc, 14 mã. Chưa thấy điều kiện thoát kỹ thuật ở các lần xét thuộc
  12 mã: ACB, HCM, KLB, MSB, MZG, OCB, ORS, PVP, SAB, SSB, STB, VIC.
- 2 lần xét đã thấy điều kiện thoát kỹ thuật, thuộc VHM và VPI. Đây không phải email bán.

Chạy lại chỉ dùng OHLCV có ngày ≤ ngày xét. Thanh khoản bình quân 20 phiên trước
≥500.000 cp; tăng giá ≥2%; giai đoạn tăng/chuyển sang tăng theo MA; không cách MA50
quá 10%. Nhánh vượt cản xác nhận cần trên đỉnh 20 phiên trước và volume ≥1,4 lần;
nhánh sớm trong −1,5% đến +2,5% quanh cản và volume ≥1,1 lần; nhánh mua sớm theo
khối lượng cần gần MA10 hoặc MA50 (8%) và vượt khối lượng phiên giảm lớn nhất
trong **10 phiên trước**. Mẫu hình toàn bộ VCP, bối cảnh ngành/thị trường, quyền,
4M và CANSLIM chưa được xác nhận tại từng ngày. Không dùng báo cáo tài chính mới
nhất để giả làm thông tin đã biết trong tháng 8.

Theo dõi điều kiện thoát kỹ thuật đến 04/09: đóng cửa dưới MA50 hoặc MA200 trên 3%.
Giá tham chiếu mỗi dòng là đóng cửa ngày phát hiện; biến động luôn đo đến đóng cửa
mới nhất, kể cả khi đã thấy điều kiện thoát. Không mô phỏng khớp mua/bán, không dùng
giá đóng cửa trước lúc phát hiện làm giá giao dịch, không tính lợi nhuận chiến lược.
Thiếu phiên theo dõi được gắn nhãn chưa xác minh. Sự kiện doanh nghiệp và điều chỉnh
giá chưa được kiểm chứng đầy đủ; kết quả chỉ là bước lọc để nghiên cứu tiếp.

## Tái lập và cập nhật

```powershell
python scripts/build_recommendation_history.py --history private-staging/history.csv --as-of 2026-09-04
python -m unittest engine.tests.test_recommendation_history
python scripts/build_production.py
```

Đầu ra công khai chỉ chứa nội dung cảnh báo đã đối chiếu và quan sát tổng hợp,
không kèm toàn bộ bảng giá đầu vào hay thư riêng. Hai bộ dữ liệu giữ schema riêng:
VERIFIED_EMAIL_HISTORY và RETROSPECTIVE_TECHNICAL_SCREEN. File công khai giữ mốc
giá và mốc rà soát thư rõ ràng, không tự nhận là cập nhật trong phiên.

Để cập nhật kết quả, dùng lịch sử giá mới và --as-of mới. Để cập nhật trạng thái
email bán, trước hết đối chiếu email mới rồi thêm sự kiện vào sổ gốc; cập nhật giá
không tự làm tăng mốc đã rà soát thư. Chưa nối quyền truy cập Gmail vào máy chủ.

## Kiểm chứng

Kiểm thử chống dùng giá tương lai, trùng phiên, tự điền phiên thiếu, đếm lặp lần
DCM cập nhật, bán thiếu chứng cứ, lãi/lỗ khi chưa có giá và lộ địa chỉ người nhận.
Kiểm tra trình duyệt desktop/mobile: 2 mã gốc, 25 dòng rà soát, bộ lọc mã/trạng thái,
thời gian Gmail, mức biến động, cuộn bảng trong khung và tải lỗi không hiển thị số 0.
