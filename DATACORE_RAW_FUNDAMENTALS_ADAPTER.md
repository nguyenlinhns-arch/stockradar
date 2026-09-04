# DataCore Fundamentals → StockRadar RAW Financial Contract

## Vai trò

DataCore chỉ được dùng để cung cấp **các khoản mục báo cáo tài chính gốc**. StockRadar không nhập ROE, EPS, P/E, P/B, PEG, EV/EBITDA, score, rank, Fair Value, target hay recommendation đã tính sẵn.

Datasets được adapter cho phép:

- `fundamental_annual`
- `fundamental_quaterly`

Catalog DataCore mô tả đây là báo cáo kết quả kinh doanh, bảng cân đối kế toán và lưu chuyển tiền tệ của doanh nghiệp niêm yết Việt Nam.

## Các line item StockRadar sử dụng

- Doanh thu thuần
- LNST / LNST thuộc cổ đông
- Tổng tài sản
- Vốn chủ sở hữu
- Tiền & tương đương tiền
- CFO
- CAPEX
- Các khoản vay/nợ thuê tài chính để StockRadar tự cộng thành total debt
- Lợi nhuận hoạt động nếu có
- Khấu hao nếu có

Số cổ phiếu dùng trong `fundamentals.csv` lấy từ raw HOSE security master/SSI market identity, không lấy EPS của DataCore.

## Các phép tính thuộc StockRadar

Từ các line item trên, StockRadar tự tính tăng trưởng doanh thu/LNST, ROE, margin, D/E, FCF, Owner Earnings, EPS, P/E, P/B, PEG, EV/EBITDA, DCF Bear/Base/Bull, Fair Value, MOS, Payback và StockRadar Score.

## Credentials

Adapter chỉ đọc API key từ môi trường:

- `DATACORE_API_KEY`, hoặc
- `X_API_KEY` (tên biến của official DataCore Python SDK).

Không ghi key vào repo, Drive, output CSV, metadata hoặc log.

## Data Rights Gate

SDK/client code công khai của DataCore dùng MIT **không đồng nghĩa dataset được phép tái phân phối công khai**. Production vẫn yêu cầu bằng chứng riêng cho:

- `publication_allowed = true`
- `redistribution_allowed = true`
- `source_terms_reviewed = true`
- `evidence_ref`

Nếu chưa có bằng chứng này, StockRadar có thể dùng dữ liệu trong nghiên cứu nội bộ nếu hợp đồng cho phép, nhưng `Top HOSE` công khai vẫn fail-closed.
