# StockRadar Production Data Source Decision

Decision date: 2026-09-03.

## Decision

StockRadar will use a two-lane data architecture:

1. **Private research/alert lane:** DNSE LightSpeed Market Data may remain the source for the owner's private scanner and owner-only operational alerts, subject to the DNSE account terms.
2. **Customer/public lane:** use only a provider/contract that explicitly grants public display, redistribution and derived-data rights for StockRadar's website, paid users, rankings, signals and recommendations.

The two lanes must not be silently mixed.

## Provider status

### DNSE LightSpeed Market Data — INTERNAL_ONLY

Technical fit: strong for realtime/intraday OHLC, trades, market status and streaming.

Public-product rights gate: blocked. Current DNSE LightSpeed API terms prohibit providing API information/data to third parties, including processed information, unless redistribution is approved in writing and required exchange/regulatory procedures are completed.

Use now: private engine only. Do not use a DNSE-backed bundle to set `rights.redistribution_allowed=true` without written approval evidence.

### FiinGroup API Datafeed — REVIEW_REQUIRED / PRIMARY COMMERCIAL CANDIDATE

Technical documentation shows coverage that maps closely to the StockRadar production contract:

- listed-company/security master data;
- HOSE market/trading data;
- financial statements and corporate financial ratios;
- corporate-event data;
- ownership/foreign-flow and other market/corporate datasets.

This makes FiinGroup the first commercial source to evaluate for the public/customer lane. Technical availability does not imply redistribution rights. The Data Gate stays closed until the signed agreement is reviewed.

Technical documentation: `https://datafeed.fiingroup.vn/`
Contact: `https://datafeed.fiingroup.vn/lien-he`

### HOSE direct information service — PARALLEL OFFICIAL OPTION

HOSE publishes an information-service price schedule and supports contracted information services. This is the authoritative-market-source path to evaluate in parallel, especially if a direct market-data license is preferable.

A direct HOSE feed would still need a complementary licensed source for fundamentals/corporate data if the contracted product does not cover all fields required by StockRadar.

## Commercial-rights questions that must be answered in writing

Before signing any provider, obtain explicit answers for:

1. May StockRadar display the data on a public website?
2. May StockRadar show the data to registered Free users and paying users?
3. May StockRadar calculate and display derived scores, rankings, technical indicators, Fair Value, Buy Zone, Stop, Target and Risk/Reward?
4. May StockRadar send customer email alerts derived from the provider data?
5. Are raw values allowed to be redistributed, or derived values only?
6. Are realtime, delayed, intraday and EOD rights different?
7. What cache/retention/history period is permitted?
8. Are VN-Index/VN30/index values included in display/derived-data rights?
9. Are corporate actions and adjusted-price histories included and contractually supported?
10. What end-user/device/session limits apply?
11. What attribution is mandatory?
12. What are the request/streaming limits, SLA, incident process and support hours?
13. Is sublicensing or customer-facing API access prohibited?
14. What audit/provenance records must StockRadar keep?
15. What are the effective date, renewal, termination and post-termination deletion obligations?

## Technical acceptance checklist

A provider is not production-ready until it can populate one fresh manifest containing:

- `security_master`;
- `ohlcv`;
- `fundamentals`;
- `corporate_actions`;
- `events`;
- active/tradable status semantics;
- same-snapshot reconciliation;
- checksum/provenance;
- `DECISION_GRADE` data quality;
- signed rights evidence reference.

The manifest must pass:

```bash
python scripts/validate_production_data.py /secure/path/production-manifest.json --max-age-hours 6
```

Only then may GitHub Pages or another production frontend publish unblocked StockRadar data.
