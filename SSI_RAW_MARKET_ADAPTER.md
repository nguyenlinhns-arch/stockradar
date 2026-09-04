# SSI FastConnect → StockRadar RAW Market Contract

## Vai trò

SSI FastConnect chỉ là **nguồn vận chuyển dữ liệu thị trường thô**. Không có score, rating, ranking, recommendation hay chỉ báo tính sẵn của SSI được đưa vào engine StockRadar.

## Dữ liệu được phép lấy

- `SecuritiesInfo`: `symbol`, `board`, `symbol_name_vi`, `listed_shares`, `icb_code`, `icb_name`, `first_trading_date`.
- `OHLCData`: `symbol`, `trading_date`, `open_price`, `high_price`, `low_price`, `close_price`, `volume`, `value`.
- OHLCV daily và 5-minute phục vụ tính toán nội bộ.

## Dữ liệu bị cấm

- Provider score / rating / rank / recommendation / target.
- Provider technical indicators / RS / RVOL / Stage / VCP / VPA.
- Provider valuation ratio / Fair Value / MOS / Buy Zone / Stop / Target / R:R.

## Credentials

Chỉ đọc từ biến môi trường:

- `SSI_FASTCONNECT_CLIENT_ID`
- `SSI_FASTCONNECT_API_KEY`
- `SSI_FASTCONNECT_API_SECRET`

Không ghi credentials vào repo, Google Drive, log, metadata hoặc public artifact.

## Production gate

Có API credentials **không đồng nghĩa** có quyền xuất bản/redistribute dữ liệu. `publication_allowed`, `redistribution_allowed` và `source_terms_reviewed` vẫn phải có bằng chứng riêng trước khi `ProductionDataGate` cho phép `Top HOSE` public.

## Pipeline

`SSI raw Securities/ICB + raw OHLCV` → `StockRadar raw bundle` → `StockRadar corporate-action normalization` → `StockRadar internal benchmark` → `StockRadar Auto Research/Valuation` → `StockRadar Score` → `Top mạnh nhất / Top theo ngành`.

Fundamentals/BCTC vẫn phải đi vào dưới dạng line-item thô từ nguồn có quyền; adapter SSI market không tự tạo BCTC.
