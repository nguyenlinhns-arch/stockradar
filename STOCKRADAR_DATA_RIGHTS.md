# StockRadar Data Rights and Provenance Gate V2

Status: **BLOCKED for production**.

## Source registry fields

Provider, dataset/field, access method, license owner, permitted purposes, display/redistribution rights, derived-data rights, retention, territory, attribution, refresh limit, effective/expiry dates, security owner and approval evidence.

## Gates

1. Legal/contract owner confirms commercial use.
2. Engineering proves timestamp, field mapping and reconciliation.
3. Product confirms the public display is within licensed rights.
4. Security confirms credential handling and access logging.
5. Compliance approves claims and attribution.

Unknown rights fail closed. Public websites, scraped pages and user subscriptions are not presumed to permit systematic ingestion, redistribution or commercial derived rankings.

## Provenance per observation

`source_id`, source timestamp, ingestion timestamp, symbol/exchange, raw reference/hash, adjustment basis, corporate-action status, quality grade and correction link.

The current fixture source `STOCKRADAR_DEMO_FIXTURE` is MOCK and grants no inference about production data availability or rights.

## 2026-09-02 internal HOSE directory reference

- Snapshot: `hose-universe-2026-09-02-065632-vn`.
- Structural validation: 405/405 records.
- Observed raw listing-status value: `11`; its active/tradable semantics are not yet approved.
- Missing production layers: licensed OHLCV, corporate actions, fundamentals and event data.
- Public rule: expose summary readiness only. Do not publish the 405 raw/normalized rows, membership claims, rankings or recommendations until redistribution rights and field semantics are approved.

## DNSE LightSpeed API — internal use only until written redistribution approval

Official DNSE LightSpeed API terms state that API information/data is for the customer's own securities-trading purpose and must not be provided to third parties, including processed information derived from the original API data. Redistribution/service provision to third parties requires written notice, DNSE approval and any required exchange/regulatory procedures.

Operational rule for StockRadar:

- DNSE Market Data may continue to power the private PC/VPS scanner, research workflow and owner-only alerts under the applicable account terms.
- Do **not** publish raw DNSE data, processed DNSE data, public rankings, paid alerts or customer-facing recommendations derived from DNSE Market Data until written redistribution/derived-data approval is recorded in the source registry.
- `rights.publication_allowed`, `rights.redistribution_allowed` and `rights.source_terms_reviewed` must remain false for a DNSE-backed public bundle until approval evidence exists.
- API keys, secrets, tokens and OTP material never enter the production-data manifest, Git repository, public Pages artifact or Drive data bundle.

References reviewed 2026-09-03:

- DNSE LightSpeed API terms: `https://hdsd.dnse.com.vn/die-u-khoa-n-di-ch-vu-dnse/dieu-khoan-san-pham-dich-vu/dieu-khoan-san-pham-lightspeed-api`
- DNSE OpenAPI Market Data documentation: `https://developers.dnse.com.vn/docs/dnse/market-data/`

## Candidate public-data vendor — FiinGroup API Datafeed

FiinGroup API Datafeed documentation shows technical coverage relevant to StockRadar, including listed-company master data, HOSE market data, corporate events and other market/corporate datasets. This is a **technical candidate only**, not an approved production source.

Before use, obtain a commercial agreement that explicitly covers the StockRadar use case: public website display, paid-user access, derived rankings/signals/recommendations, retention/cache, refresh frequency and redistribution territory. Until written rights are recorded, the provider remains `REVIEW_REQUIRED` and the public Data Gate remains closed.
