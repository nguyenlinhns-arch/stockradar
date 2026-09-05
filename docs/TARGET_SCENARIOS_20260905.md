# Target dự kiến và stoploss — 05/09/2026

Mục tiêu dự kiến là kịch bản nghiên cứu có công thức, không phải cam kết giá hoặc tín hiệu mua. Khi đã có báo cáo hành động được phát hành, dùng các mức của đúng báo cáo và thời hạn đó.

## Kịch bản AI

Đầu vào phải thuộc mã đủ dữ liệu nghiên cứu, có giá dương và không bị gắn cũ/lỗi. Kỳ kế toán không được sau ngày quan sát. Trường thiếu không biến thành 0.

- **Ngắn hạn:** mốc vào giả định = pivot quan sát. Khoản lỗ mô hình = 1,5 × ATR20%, giới hạn 5–8%, theo quy tắc vốn hiện có của decision engine. Stoploss = mốc vào × (1 − khoản lỗ%). Mục tiêu quản trị vốn = mốc vào + 2 × (mốc vào − stoploss). Không phải dự báo xác suất đạt giá. Thiếu pivot hoặc ATR thì không tính.
- **3 / 6 / 12 tháng:** doanh nghiệp thông thường dùng EPS TTM và P/E trung vị 8 quý. Ngân hàng/chứng khoán/bảo hiểm dùng BVPS và P/B trung vị 8 quý. Công thức: chỉ tiêu trên mỗi cổ phiếu × (1 + tăng trưởng giả định)^(số tháng / 12) × hệ số lịch sử.
- Với EPS, ưu tiên tăng trưởng EPS nếu có. Nếu thiếu, mô hình dùng mức thấp hơn trong các số tăng trưởng doanh thu hiện có và nêu rõ giả định biên lợi nhuận/số cổ phiếu không đổi. Không coi tăng trưởng lợi nhuận trước thuế là tăng trưởng EPS.
- Với BVPS, mô hình dùng tăng trưởng vốn chủ sở hữu và nêu rõ giả định số cổ phiếu không đổi. Nếu thiếu tăng trưởng, dùng kịch bản tăng trưởng 0 được ghi rõ là giả định.
- Tăng trưởng mô hình giới hạn −30% đến +20%/năm. Đây là lựa chọn mô hình, không phải dữ liệu nguồn hoặc kết quả hiệu chuẩn.
- **Tích sản:** ngưỡng tham khảo = 80% kịch bản 12 tháng. Biên dự phòng 20% là giả định mô hình; chưa xác nhận giá trị nội tại hoặc điểm tích sản.
- Cắt lỗ kỹ thuật ngắn hạn không được gán chung cho tất cả thời hạn.

Toàn bộ phép tính dùng số nguồn đầy đủ trước khi làm tròn để hiển thị. Kịch bản có thể thấp hơn giá đang quan sát. Chưa đánh giá đầy đủ thay đổi biên lợi nhuận, pha loãng, sự kiện doanh nghiệp, hệ số thị trường và chu kỳ; vì vậy nhãn là độ tin cậy thấp, giả định chưa được xác minh. Không ghi xác suất thành công.

Dữ liệu trả về nằm trong `estimated_plan`; `analysis.targets` và các cờ cho phép hành động không được nâng cấp bởi kịch bản này. Cùng module dùng cho khách và người đăng nhập, tự tính lại từ context mới của mỗi lần hỏi.

## Email

Email gửi mức của báo cáo chính thức, theo horizon; không lấy kịch bản AI để tự phát hành hành động. Ba target và stoploss được giữ từ producer đến kiểm tra ngay trước khi gửi. Thiếu target 12 tháng không được thay bằng target ngắn hạn rồi đổi nhãn.

Mua/mua thêm chỉ qua worker nếu có vùng vào hợp lệ, stoploss dưới đáy vùng vào và target của đúng thời hạn cao hơn đỉnh vùng vào. Báo cáo thiếu mức bị chặn và có mã lý do. Email bán/giảm vị thế vẫn có thể được gửi mà không cần dựng thêm target mua.

Không có thay đổi nào tự bật quyền gửi email, quyền phát hành khuyến nghị hoặc quyền thu tiền.
