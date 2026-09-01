# StockRadar Product Specification V2.1.2

Status: current MVP contract, 2026-09-01. It incorporates Change Request V2.1, Execution Priority Addendum V2.1.1 and Change Request V2.1.2. It supersedes V1/V2 wherever they conflict; non-conflicting controls remain in force.

## Product promise

StockRadar helps a Vietnamese self-directed investor filter, evaluate, monitor, receive relevant reminders, verify history and personalize the service. The primary flow is `SHOW VALUE → FREE SIGNUP → PAID CONVERSION → RETENTION`.

It is a research and education product. A ranking is not a recommendation, a score is not a win probability, and no output is individualized investment advice or an order.

## Four independent horizons

| Horizon | Holding window | Primary evidence | Risk logic |
| --- | --- | --- | --- |
| Short | 5–20 sessions | trend, RS, VPA, VCP/pivot, volume, liquidity, extension | technical invalidation and same-horizon R:R |
| Medium | 1–6 months | trend, growth, sector, flow, catalyst, valuation | same-horizon target and risk |
| Long | 6–18 months | business quality, moat, management, cash flow, fair value | thesis invalidation; no copied short-term stop |
| Accumulation | 2–5+ years | 4M, balance sheet, cash return, margin of safety | business/thesis exit conditions |

## Decision architecture

1. Freeze the source snapshot and provenance.
2. Grade data and enforce full-universe truthfulness.
3. Score only the chosen horizon with non-duplicated evidence.
4. Rank research candidates.
5. Apply a separate Recommendation Gate for data, staleness, coverage, liquidity, event risk, extension, market context, contradictions and horizon-consistent plan fields.
6. Publish an immutable recommendation as `UNACTIVATED`.
7. Activate only on the first eligible post-publication trade in the buy zone.
8. Measure open/closed performance from the performance entry, with corporate-action and benchmark controls.
9. Require a review by `review_due_at`; append CONTINUE, ADJUST, NO_LONGER_ELIGIBLE or CLOSE to the journal.

## Universal HOSE lookup architecture

The user experience must accept any ticker in the current HOSE security master. HPG/MBB/FPT/VCI are examples only. Input is normalized to uppercase and validated against the current master; StockRadar does not invent a report, silently change exchange or return a deep-analysis 404 merely because cache is absent.

The production design has three layers:

1. Light full-HOSE scan 1–2 times/day for universe, price/OHLCV, liquidity, trend, RS, volume, sector, basic flags and ranking candidates.
2. Deep analysis on demand for four horizons, new-position/holding views, thesis, risk, valuation, recommendation and journal. Cache is keyed by ticker + horizon + report type and has horizon-specific TTL.
3. Intraday monitoring only for the deduplicated union of active recommendations, near-trigger candidates and Trial/Paid watchlists.

On-demand lookup never replaces the full-universe gate for Top 10, Top sector or “strongest HOSE” claims. Anonymous lookup and deep analysis require configurable rate limits, throttling, timeout, fallback, queueing and observability.

## Public information architecture

The eight primary destinations are Home, Cổ phiếu nổi bật, Theo ngành, Khuyến nghị, Hôm nay có gì thay đổi, Phân tích cổ phiếu, Hiệu quả, and Tài khoản/Nâng cấp. Knowledge, paid email, watchlist and publication audit remain secondary navigation.

Home is a live-demo surface, not a text-first marketing page. Above the fold it asks for a ticker and returns price/freshness when licensed, sector/rank, four horizon views, new-position and holding views, recent recommendation history and a ticker-specific Trial CTA. A 30–60 second Today Changes view shows only meaningful changes.

## Stock-report contract

Every ticker report separates: four independent horizon assessments and freshness; new-position view; existing-holder view; 3–5 reasons; risks; conditions that change the view; current recommendation; immutable journal; recommendation history; and VN-Index comparison when the matching-window benchmark is available. “Not suitable for a new buy” never implies “must sell.”

## Entitlements and price test

- Public: quick lookup, basic four-horizon view, partial ranking, public recommendation list/history/P&L, performance and a sample report.
- Free: public value plus end-of-session Top 10 when eligible, basic sector view, summary reports, personalization and 1–3 watchlist tickers. Free users receive transactional email only and never daily product content.
- Trial (7 days): up to three watchlist tickers and personalized product email only after verification and consent.
- Advanced: full reports, buy zone/target/risk, journal/history, around 20 watchlist tickers, personalized daily/change emails and paid-only updates.
- Standard planned price: 299,000 VND per 30 days.
- Founding test price: 199,000 VND per 30 days.
- No charge may occur while billing, privacy, security, data-rights or compliance gates are blocked.

The 30-day value is ongoing monitoring, evaluation, update, reminder, journal and P/L maintenance—not merely website access.

## Current implementation boundary

The code implements lookup/autocomplete contracts, dynamic ticker shell, quick/partial result handling, cache, independent TTL, watchlist deduplication, intraday-universe union, rate-limit reference logic, analytics and regression tests. The Pages artifact uses a visibly MOCK reference fixture and cannot claim full-HOSE support. Licensed current security master/data, production queue/cache, auth, email and billing remain blocked.

## Explicitly out of scope before Ads evidence

No board/terminal, native app, forum/social, chart suite, newsfeed, large AI chatbot, portfolio NAV, commercial API or new indicator. Expansion requires activated Free users, D1/D7, paid conversion, CAC and renewal evidence.

## Operational modes

`INTERNAL`, `RESEARCH_ONLY`, `COMPLIANCE_REVIEW`, `PRODUCTION_APPROVED`. GitHub Pages is fixed to `RESEARCH_ONLY`, static/no-write, MOCK/SHADOW and noindex.

## Production gates

Production requires licensed current HOSE data; reproducible full-universe reconciliation; four horizon calibrations; resolved corporate actions and benchmark source; shadow history; secure auth, privacy operations, email and billing; monitoring and correction procedures; data-rights approval; formal Vietnamese compliance/legal review; and `PRODUCTION_APPROVED` mode. Until every gate passes, the product must not claim live Top HOSE, production recommendations, production performance or paid readiness.
