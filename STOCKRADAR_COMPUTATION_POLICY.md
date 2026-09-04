# StockRadar Internal Computation Policy

## Nguyên tắc bắt buộc

StockRadar không nhập và không sử dụng điểm số, xếp hạng, tín hiệu, định giá hoặc khuyến nghị đã được tính sẵn bởi bất kỳ nhà cung cấp dữ liệu bên ngoài nào.

Nguồn bên ngoài, nếu được sử dụng và có đủ quyền, chỉ được cung cấp **RAW INPUT** cần thiết để StockRadar tự tính toán.

## Dữ liệu đầu vào được phép

- Security master / mã / tên doanh nghiệp / sàn / thông tin nhận diện.
- OHLCV thô: thời gian, Open, High, Low, Close, Volume, giá trị giao dịch nếu có.
- Báo cáo tài chính thô: doanh thu, lợi nhuận, tài sản, vốn chủ, nợ, tiền, dòng tiền hoạt động, CAPEX, số cổ phiếu và các line item gốc.
- Corporate actions thô: cổ tức, quyền mua, chia/tách, phát hành, ngày hiệu lực.
- Sự kiện/catalyst thô có nguồn và thời gian xác định.

## Dữ liệu bên ngoài bị cấm đi thẳng vào engine quyết định

- Score / rating / rank / sector rank.
- Buy/Sell/Hold signal, recommendation, target price.
- MA/EMA/SMA, RSI, MACD, Bollinger, Ichimoku, Relative Strength, RVOL.
- Stage, VCP, Pivot, Pocket Pivot, Breakout, Retest, VPA/accumulation/distribution.
- P/E, Forward P/E, P/B, PEG, EV/EBITDA, ROE, ROA, ROIC và các ratio tính sẵn.
- FCF, Owner Earnings, Payback, Fair Value, Sticker Price, MOS.
- Buy Zone, Stop-loss, Target, Upside, Downside, Risk/Reward, Expected Return, probability.
- Giá đã điều chỉnh sẵn nếu corporate actions chưa được StockRadar tự chuẩn hóa.

## Chuỗi tính toán nội bộ

`RAW INPUT → chuẩn hóa StockRadar → 4M/Payback → CANSLIM → định giá → SEPA/VCP/Stage → VPA → Pocket Pivot/Early Momentum → Ichimoku/Bollinger/Trendline → dòng tiền/market → điểm mua → risk management → Top HOSE / Decision Card`

Mọi output dùng để xếp hạng hoặc ra quyết định phải có provenance:

- `calculation_origin = STOCKRADAR_ENGINE`
- `external_input_role = RAW_INPUT_ONLY`
- `external_scores_accepted = false`

Production Data Gate phải fail-closed nếu vi phạm một trong các điều kiện trên.
