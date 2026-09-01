# StockRadar GPT/API Contract

Minimum read operations:

- `getCalendarStatus`
- `getMarketSnapshot`
- `getHoseUniverseStatus`
- `getRadarByHorizon`
- `getSectorRankingByHorizon`
- `getStockReport`
- `getActiveRecommendations`
- `getRecommendationHistory`
- `getPerformanceSummary`
- `getBreakoutRadar`
- `getRiskRadar`
- `getTrackRecord`
- `getStateChanges`

Every dynamic response must include:

- `schema_version`
- `snapshot_id`
- `as_of`
- `source_timestamp`
- `data_grade`
- `source/provenance`
- `market_regime`
- universe total/scanned/valid/excluded/Coverage where ranking is involved
- conflicts and correction lineage when present.

Recommendation responses additionally include:

- `recommendation_id`, `ticker`, `horizon`, publication time and expiry;
- immutable buy zone/price at publication/target/invalidation;
- separate publication timestamp, activation timestamp and performance entry price;
- current-price observation with its own timestamp;
- close price/time/reason/final return for closed records;
- price/total return basis, corporate-action references, benchmark and excess return;
- record mode (`BACKTEST`, `SHADOW`, `LIVE_PUBLISHED`) and recommendation mode;
- evidence score, Coverage and explicit `score_is_probability=false`;
- thesis, risks, invalidation conditions and public state;
- action gate results, including unknown/blocked reasons;
- `is_mock`, whenever applicable.

Writes are separate authenticated operations for watchlist preference and email consent. They must never accept broker credentials, OTPs, orders, NAV or portfolio-control authority.

The local engine produces the Radar payload, but no HTTPS API/authentication exists. Do not configure a fake Action hostname.

Production requirements:

- HTTPS base URL;
- OpenAPI schema;
- API key or OAuth stored outside prompts/files;
- rate limits and bounded retries;
- idempotent snapshot/alert identifiers;
- semantic integration tests, not HTTP 200 alone.

The static GitHub Pages build exposes no write endpoint and must return a clear unavailable state rather than pretending that watchlist, login, payment or email delivery succeeded.
