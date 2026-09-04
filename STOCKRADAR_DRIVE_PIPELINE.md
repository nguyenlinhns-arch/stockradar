# StockRadar Drive Data Pipeline

Updated: 2026-09-04 (Asia/Ho_Chi_Minh)

## Canonical private data store

Google Drive folder `Chứng khoán/04 - Dữ liệu StockRadar` is the private single source of truth for StockRadar research/scanner inputs. The public GitHub repository contains code, schemas, QA rules and publish-safe artifacts only.

Current internal coverage verified on 2026-09-04:

- Canonical HOSE universe: 405/405 tickers.
- Daily OHLCV: 405/405.
- Latest snapshot: 405/405.
- Technical feature store: 405/405.
- Fundamental feature store: 405/405.
- Relative Strength: 405/405.
- Intraday 5m: 403/405.
- Internal valuation bootstrap: 405/405.
- Internal scanner master: 405/405.
- Internal website feed: 405/405.

## Private pipeline

`HOSE master -> OHLCV + intraday + company fundamentals + corporate actions/events -> QA -> derived technical/fundamental/valuation features -> scanner master -> ranking/action gate -> internal website feed`

The scanner implements the project sequence:

`4M/Payback -> CANSLIM -> valuation -> SEPA/VCP -> VPA -> Pocket Pivot/Early Breakout -> Ichimoku/Bollinger/Stage -> liquidity/flow -> risk/reward -> action gate`.

## Public boundary

Internal data readiness and publication authorization are separate gates.

The current Drive bundle may be used for private research, model development, QA and scanner calculation. It must not be copied into the public repository or published as live market/recommendation output until all of the following pass:

1. Contracted data source and written rights for the intended public/derived-data use.
2. Current exchange/listing-status semantics.
3. Freshness and full-universe reconciliation.
4. Corporate-action adjustment checks.
5. Production manifest and exact snapshot binding.
6. Decision-grade model output and risk fields.
7. Compliance/legal approval.
8. Production activation flag.

## Private staging contract

When an authorized operator exports the current Drive bundle to a local/private runtime, stage it under `private-staging/` or another non-versioned secure directory. This path is ignored by Git.

Validate it with:

```bash
python scripts/validate_private_scanner_bundle.py private-staging --output qa-output/private-scanner-gate.json
```

`PASS_INTERNAL` confirms structural scanner usability only. It never authorizes publication.

## Website integration

The website must consume only a publish-safe cache produced after the publication gate. Public pages fail closed when an approved active manifest is unavailable. No personal-priority ticker metadata may be included in the website feed.

## Operational target

During trading sessions, refresh the private data pipeline ahead of the four project scan checkpoints: 10:30, 11:15, 13:30 and 14:15 Vietnam time. Intraday scoring must use progress-adjusted/same-time volume rather than applying full-day volume mechanically.
