# StockRadar GPT/API Contract

Minimum read operations:

- `getCalendarStatus`
- `getMarketSnapshot`
- `getHoseUniverseStatus`
- `getRadar5`
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

The local engine produces the Radar payload, but no HTTPS API/authentication exists. Do not configure a fake Action hostname.

Production requirements:

- HTTPS base URL;
- OpenAPI schema;
- API key or OAuth stored outside prompts/files;
- rate limits and bounded retries;
- idempotent snapshot/alert identifiers;
- semantic integration tests, not HTTP 200 alone.

