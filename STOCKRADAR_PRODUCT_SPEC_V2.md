# StockRadar Product Specification V2

Status: frozen MVP contract, 2026-09-01. This document supersedes V1 wherever the two conflict.

## Product promise

StockRadar helps a Vietnamese self-directed investor answer three jobs: which stocks deserve attention for a chosen holding horizon, what a specific ticker's conditional plan says, and how published recommendations performed under a fixed methodology.

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

## Public information architecture

The seven primary destinations are Home, Cổ phiếu nổi bật, Theo ngành, Khuyến nghị, Phân tích cổ phiếu, Hiệu quả, and Tài khoản/Nâng cấp. Knowledge, email, watchlist and publication audit remain secondary navigation.

Public pages must show value before signup: a horizon-ranked demo, ticker search, recommendation lifecycle, sample nine-question report and transparent performance methodology.

## Nine stock-report questions

Current evaluation; horizon rank; current price position; buy zone and activation/entry; target and invalidation; thesis; principal risks; what changes the view; prior recommendation/performance audit.

## Entitlements and price test

- Free: public ranking demo, ticker DEMO report, public lifecycle/performance, Knowledge.
- Advanced: full horizon/sector depth, nine-question reports, pre-session email, state-change alerts, watchlist and recommendation history.
- Standard planned price: 299,000 VND per 30 days.
- Founding test price: 199,000 VND per 30 days.
- No charge may occur while billing, privacy, security, data-rights or compliance gates are blocked.

## Operational modes

`INTERNAL`, `RESEARCH_ONLY`, `COMPLIANCE_REVIEW`, `PRODUCTION_APPROVED`. GitHub Pages is fixed to `RESEARCH_ONLY`, static/no-write, MOCK/SHADOW and noindex.

## Production gates

Production requires licensed current HOSE data; reproducible full-universe reconciliation; four horizon calibrations; resolved corporate actions and benchmark source; shadow history; secure auth, privacy operations, email and billing; monitoring and correction procedures; data-rights approval; formal Vietnamese compliance/legal review; and `PRODUCTION_APPROVED` mode. Until every gate passes, the product must not claim live Top HOSE, production recommendations, production performance or paid readiness.
