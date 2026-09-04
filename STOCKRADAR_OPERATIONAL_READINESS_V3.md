# StockRadar Operational Readiness V3

Updated: 2026-09-04 (Asia/Ho_Chi_Minh)

## Objective

StockRadar is not considered operational merely because it has 405 tickers and technical indicators. A production-grade Radar must be able to answer, for every HOSE ticker, whether the data are trustworthy, whether the stock is tradable, whether the company and valuation pass, whether market/sector context supports the setup, whether money flow confirms it, and what invalidates the trade.

## Current private coverage

| Layer | Coverage / status | Operational rule |
| --- | --- | --- |
| HOSE security master | 405/405 | Full-universe scan source |
| Daily OHLCV | 405/405 | Internal research only until rights/reconciliation pass |
| Intraday 5m | 403/405 | LGC/TTE excluded from intraday actions; no false zero-volume projection |
| >=210-session technical history | 394/405 | Never synthesize MA200 for young/sparse listings |
| Fundamentals | 405/405 | Usable internally; reconcile with contracted raw statements before publication |
| Base valuation | 400/405 | Five incomplete valuations cannot receive full valuation confidence |
| Sector classification | 405/405 after 3 provisional overrides | Overrides require provider-taxonomy reconciliation |
| VNINDEX + market breadth | PASS_INTERNAL | Market regime is a required ranking/action input |
| Foreign buy/sell snapshot | 405/405, limited depth | Current flow is context, not an institutional trend signal |
| News | 405 rows but only one headline/ticker in current bundle | Catalyst weight = 0 until multi-page depth/freshness pass |
| Corporate actions | FAILED quality gate | Current bootstrap is stale/empty; cannot drive ex-rights or adjustment logic |
| Insider/proprietary/institutional | Missing from operational Drive bundle | Required to complete CANSLIM-I/Whale confirmation |
| Public data rights/compliance | BLOCKED | Public live recommendations remain fail-closed |

## Market regime V3

The market layer deliberately separates index trend from breadth. On the 2026-09-04 snapshot, VN-Index trend remains above the major moving averages while breadth is materially weaker: advancers are below decliners, only a minority of HOSE stocks are above MA50/MA200, and Stage-2 breadth is narrow. The resulting internal classification is `PHAN_HOA_THAN_TRONG` rather than broad risk-on.

This prevents the model from treating a rising headline index as permission to buy across the board.

## Ranking policy V3

`radar_rank_score_v3 = 72% core StockRadar + 13% sector strength + 7% market regime + 8% inverse risk`.

Core StockRadar retains company/fundamental, valuation, technical/SEPA-VCP, VPA/flow and liquidity inputs. Sector and market context now explicitly affect ranking. Risk uses ATR/realized volatility/drawdown/liquidity measures.

Catalyst weight is currently **zero** because the available news bundle is not deep enough. Corporate actions are a **quality/risk gate**, not an alpha score; the current event source does not pass.

## Action Gate

A ticker cannot become an action candidate merely because its raw score is high. At minimum it must pass:

1. current HOSE universe identity;
2. sufficient technical history or an explicitly permitted early-entry exception;
3. real liquidity threshold;
4. fundamental readiness;
5. valuation readiness appropriate to the horizon;
6. sector/context readiness;
7. intraday volume integrity for intraday setups;
8. risk limits and non-extended price structure;
9. valid Pocket Pivot / Early Breakout / Confirmed Breakout / Retest state;
10. event/corporate-action verification before production publication;
11. data-rights and compliance publication gate.

## Website rule

There is no fixed `Radar 30` recommendation list. The website must render a dynamic, snapshot-bound subset generated from the full HOSE scanner. If an approved live manifest does not exist, it must fail closed rather than display sample or manually curated tickers.

## Next data acquisitions

Priority order:

1. current authoritative corporate actions / ex-rights / dividends / issuance / trading-status data;
2. deeper company news, material-event classification and catalyst scoring;
3. insider transactions, ownership changes, proprietary/institutional flow where usage rights allow;
4. 5/20-session foreign-flow history rather than one snapshot;
5. VN30, new-high/new-low, up/down volume and stronger breadth/regime evidence;
6. macro/sector drivers: rates, FX and commodity inputs mapped only to affected sectors;
7. licensed/contracted production data rights and compliance approval.

Until those gates pass, the private engine may rank/research candidates, but public live recommendations must remain disabled.
