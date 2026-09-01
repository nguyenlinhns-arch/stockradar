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
