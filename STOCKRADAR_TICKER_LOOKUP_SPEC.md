# StockRadar Ticker Lookup and Cache Specification V2.1.2

## Contract

Normalize submitted ticker to uppercase and validate it against the current HOSE security master. Autocomplete reads the master only; it never runs deep analysis while typing. Unknown/non-HOSE values do not generate a report or silently move to another exchange.

## Three layers

1. Full-HOSE light snapshot for Top/sector claims and quick public fields.
2. On-demand deep analysis for searched, ranked, recommended or popular/watchlisted tickers.
3. Deduplicated intraday active universe for recommendations, near-trigger candidates and Trial/Paid watchlists.

On-demand popularity cannot redefine the universe used by Top ranking.

## Cache

Primary key is ticker + horizon + report type. Store snapshot, generated/expiry times, data/score/report versions, payload hash, payload and freshness. A fresh hit returns without recomputation. A stale hit refreshes; a miss generates when a real analysis adapter is available. Short TTL is shorter than Medium, Long and Accumulation; material events invalidate regardless of TTL.

## Failure and cost controls

Return quick/partial result when deep data is missing. Do not promise background completion without a real queue. Production requires configurable Public/Free/Trial/Paid limits, scraping protection, throttling, queue, timeout, fallback and observability. GitHub Pages can demonstrate the UI only and cannot enforce server-side limits.
