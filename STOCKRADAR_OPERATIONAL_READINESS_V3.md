# StockRadar Operational Readiness V4

Updated: 2026-09-05 (Asia/Ho_Chi_Minh)

## Objective

StockRadar is not considered operational merely because it has 405 tickers and technical indicators. The primary production surface is now **StockRadar AI**: a synthesis/research assistant that consumes private QA-passed research data and returns concise answers for HOSE tickers and user watchlists.

The system remains fail-closed on stale data, non-HOSE contamination, invalid ticker identity and broken research snapshots.

## Current private coverage

| Layer | Coverage / status | Operational rule |
| --- | --- | --- |
| HOSE security master | 405/405 | Full-universe scan source |
| Daily OHLCV | 405/405 | Private research input; do not expose raw downloadable feed |
| Intraday 5m | 403/405 | LGC/TTE excluded from intraday actions; no false zero-volume projection |
| >=210-session technical history | 394/405 | Never synthesize MA200 for young/sparse listings |
| Fundamentals | 405/405 | Private research input with reconciliation/quality checks |
| Base valuation | 400/405 | Five incomplete valuations cannot receive full valuation confidence |
| Sector classification | 405/405 | Source/reconciliation status remains visible internally |
| VNINDEX + market breadth | PASS_INTERNAL | Required market-regime input |
| Institutional/foreign flow | Context-only | No alpha weight until semantics/history pass QA |
| News/catalyst | HOSE official depth + recall | Official evidence preferred; catalyst alpha remains controlled |
| Corporate actions | VSDC authoritative gate | Used as risk/price-adjustment gate |
| Research cache | 105/105 ready rows currently fresh | AI only consumes rows that pass freshness/quality gate |
| Raw redistribution | DISABLED_BY_DESIGN | No public raw data API/downloadable data product |
| Public action feed | OPTIONAL / disabled | Separate capability from AI research |

## Product mode

Runtime mode is `AI_ONLY`.

`Research AI` readiness does **not** depend on a blanket public-data-redistribution approval. It depends on:

1. current research snapshot freshness;
2. HOSE-only universe integrity;
3. valid ticker identity;
4. source QA/provenance;
5. no stale/invalid/failed snapshot state;
6. no public-action leakage from a closed action gate.

Raw redistribution, public downloadable datasets and public data APIs remain disabled by design.

A source whose terms explicitly prohibit third-party derived output must be excluded from customer-facing AI output even though the global AI runtime is not blocked by redistribution approval.

## Market regime

The market layer separates index trend from breadth. The AI should never treat a rising headline index as automatic permission to buy across the board. Breadth, Stage structure, liquidity and sector strength remain required context.

## Ranking and research policy

Internal ranking combines company/fundamental quality, valuation, technical/SEPA-VCP, VPA/flow, liquidity, sector context, market regime and risk.

Ranking is an internal prioritization aid. A high score is not automatically a public recommendation or an order instruction.

## Research AI gate

A ticker can be used in customer-facing StockRadar AI only when:

1. ticker is in the canonical HOSE universe;
2. research snapshot is within freshness SLA;
3. price snapshot status is not stale/invalid/failed;
4. required source joins and corporate-action checks pass for the requested analysis;
5. available technical history is sufficient for the indicator being discussed;
6. AI response clearly distinguishes research context from confirmed action state;
7. restricted source-level fields are not exposed where their terms prohibit derived third-party output.

If these conditions fail, StockRadar AI must fall back to method/context-only language and must not invent current price, Buy Zone, Stop, Target or current signal.

## Optional Action Gate

Public action/recommendation capability remains separate. If enabled later, it requires its own approval, manifest, fresh action reports and compliance controls. AI research can remain operational even while this capability is disabled.

## Website rule

StockRadar AI is the center of the website. Public static recommendation tables must remain empty/fail-closed unless a separately approved action feed exists.

The website may still show general education, account/watchlist state and AI research answers backed by the private research cache.

## Email rule

Email is a separate delivery capability. It is not blocked by the public raw-data redistribution gate, but it still requires:

1. verified sending domain;
2. provider API key stored only in secret manager/Vault;
3. working webhook for bounce/complaint/suppression;
4. unsubscribe and consent controls;
5. scheduler/worker readiness;
6. any product/compliance conditions applicable to personalized alerts.

## Runtime health

Primary healthy state: `AI_ONLY_READY`.

Expected capability states in AI-only operation:

- `research_ai = READY`
- `raw_redistribution = DISABLED_BY_DESIGN`
- `public_action = DISABLED_OPTIONAL` unless separately enabled
- `email_delivery` and `email_scheduler` independently report READY/BLOCKED

This prevents an optional public-data capability from incorrectly marking the entire AI product as unavailable.
