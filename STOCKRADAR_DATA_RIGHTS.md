# StockRadar Data Rights and Provenance Gate V3

Status: **AI_ONLY does not block on redistribution approval. Raw redistribution/public data API remain disabled by design.**

## Product mode

StockRadar currently operates in `AI_ONLY` mode. The customer-facing product is a synthesis/research assistant, not a raw market-data redistribution product.

For `AI_ONLY` operation, the runtime readiness gate is based on research freshness, HOSE-universe integrity, source QA, timestamp integrity and fail-closed behavior. A missing public redistribution approval does **not** by itself block StockRadar AI from producing synthesized research answers.

This does not convert unknown rights into approved rights. It changes the product boundary:

- do not expose downloadable raw datasets;
- do not expose a public raw-data API;
- do not mirror source tables or bulk normalized rows;
- do not make vendor raw payloads available to users;
- public action/recommendation feeds remain a separate optional capability;
- a source whose terms explicitly prohibit third-party derived output must be excluded from customer-facing AI output unless separately permitted.

## Source registry fields

Provider, dataset/field, access method, license owner, permitted purposes, display/redistribution rights, derived-data rights, retention, territory, attribution, refresh limit, effective/expiry dates, security owner and approval evidence.

## Gates by capability

### Research AI / AI synthesis

Required:

1. source identity and timestamp are known;
2. engineering field mapping/reconciliation passes;
3. research cache freshness passes;
4. HOSE-only universe contamination checks pass;
5. output is synthesis, not bulk/raw redistribution;
6. source-level restrictions that explicitly prohibit derived third-party use are respected.

Public redistribution approval is **not a global blocker** for this capability.

### Raw redistribution / public data API / downloadable feeds

Required before enabling:

1. Legal/contract owner confirms commercial redistribution rights.
2. Engineering proves timestamp, field mapping and reconciliation.
3. Product confirms the display/export is within permitted rights.
4. Security confirms credential handling and access logging.
5. Compliance approves claims and attribution.

Unknown rights fail closed for this capability.

## Provenance per observation

`source_id`, source timestamp, ingestion timestamp, symbol/exchange, raw reference/hash, adjustment basis, corporate-action status, quality grade and correction link.

The current fixture source `STOCKRADAR_DEMO_FIXTURE` is MOCK and grants no inference about production data availability or rights.

## 2026-09 HOSE operating rule

- Canonical universe is HOSE-only.
- Raw/normalized 405-row source bundles are private operational assets.
- StockRadar AI may consume QA-passed private research cache and return concise synthesized analysis.
- Public downloadable HOSE master, raw OHLCV dumps and vendor payloads remain disabled.

## DNSE LightSpeed API — source-level restriction remains authoritative

Official DNSE LightSpeed API terms reviewed by the project state that API information/data is for the customer's own securities-trading purpose and must not be provided to third parties, including processed information derived from the original API data. Therefore DNSE-backed fields remain **private/owner-only** unless written permission is obtained.

Operational rule:

- DNSE Market Data may power private owner research where applicable.
- Do not pass DNSE-derived restricted fields into customer-facing AI, public rankings, paid alerts or public recommendation outputs unless written permission is recorded.
- `rights.publication_allowed` and `rights.redistribution_allowed` remain false for DNSE-backed public bundles until approval evidence exists.
- API keys, secrets, tokens and OTP material never enter public artifacts.

## Official/public-source research

HOSE/VSDC official disclosures and other source material that passes the project source-QA rules may be summarized by StockRadar AI as research evidence. The system should prefer source links/references and synthesized conclusions over reproducing source tables verbatim.

## Candidate commercial vendor

FiinGroup and other commercial vendors may still be evaluated if StockRadar later enables raw redistribution, licensed intraday feeds or public action products. They are **not blockers for AI_ONLY research mode**.
