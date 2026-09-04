# StockRadar Licensed Provider Intake

## Purpose

This layer is the only supported entry point for a future commercial market-data provider before its raw files are allowed to enter the existing StockRadar production-data contract.

It is deliberately provider-neutral. FiinGroup/FiinPro DataFeed, SSI FastConnect + Datacore, or another vendor can be adapted to this boundary **only after a commercial agreement explicitly covers the uses below**.

This intake does **not** enable `stock_api_gate`, public ranking, recommendations, alerts, email delivery, or any broker action. It only validates rights metadata and raw inputs, then prepares a descriptor for the existing production manifest builder.

## Required private files

Keep all licensed material under an ignored/private location such as:

- `private-staging/`
- `licensed-data/`
- `production-data/`
- another server-side directory outside `website/` and `.pages-site/`

Never commit vendor raw data, credentials, tokens, contract PDFs, or confidential commercial terms to the public repository.

The intake needs:

1. raw CSV datasets in the private staging directory;
2. `package.json` — non-secret dataset/snapshot metadata;
3. `rights.json` — non-secret rights-review metadata and references only.

## `rights.json`

Example:

```json
{
  "schema_version": "1.0",
  "mode": "LICENSED",
  "provider_id": "vendor-enterprise-feed",
  "contract_ref": "MSA-2026-001",
  "evidence_ref": "rights-review/2026-09-04",
  "reviewed_at": "2026-09-04T08:00:00+07:00",
  "effective_from": "2026-09-01T00:00:00+07:00",
  "effective_until": "2027-09-01T00:00:00+07:00",
  "permissions": {
    "source_terms_reviewed": true,
    "publication_allowed": true,
    "redistribution_allowed": true,
    "internal_analytics_allowed": true,
    "derived_outputs_allowed": true,
    "customer_display_allowed": true
  }
}
```

Every permission is mandatory. `RESEARCH_ONLY`, `REFERENCE_ONLY`, unknown rights, expired rights, or any false permission are rejected before data can become a production descriptor.

`contract_ref` and `evidence_ref` are references/hashes/IDs only. Do not place contract text or secrets in these files.

### Contract language that must be resolved before enabling StockRadar production

At minimum, the signed commercial terms must permit:

- use inside a commercial/SaaS application;
- server-side storage and processing of licensed raw inputs as needed for the service;
- internal analytics and StockRadar-computed rankings/indicators;
- creation of derived outputs such as StockRadar scores, states, valuation outputs and action plans;
- customer display of permitted raw/derived information;
- redistribution/display rights needed by the actual website/email/API product surfaces;
- the required historical, daily and intraday scope;
- corporate-action handling sufficient for adjusted performance and recommendation history.

Public marketing pages from a vendor are not rights evidence. The signed contract/order form/addendum governs.

## `package.json`

Example shape:

```json
{
  "schema_version": "1.0",
  "snapshot": {
    "snapshot_id": "hose-licensed-2026-09-04-103000-vn",
    "as_of": "2026-09-04T10:30:00+07:00",
    "source_timestamp": "2026-09-04T10:30:00+07:00",
    "exchange": "HOSE",
    "expected_total": 405,
    "scanned_count": 405,
    "valid_count": 405,
    "excluded_count": 0,
    "stale_count": 0,
    "missing_count": 0,
    "data_grade": "DECISION_GRADE",
    "same_snapshot": true,
    "adjusted_basis_consistent": true,
    "corporate_action_checked": true,
    "source": "LICENSED_PROVIDER_RAW_INPUT",
    "exclusion_log": []
  },
  "active_status": {
    "semantics_resolved": true,
    "market_status_checked": true
  },
  "datasets": {
    "security_master": {
      "path": "security_master.csv",
      "ticker_column": "ticker",
      "exchange_column": "exchange"
    },
    "ohlcv": {
      "path": "ohlcv.csv",
      "ticker_column": "ticker"
    },
    "fundamentals": {
      "path": "fundamentals.csv",
      "ticker_column": "ticker"
    },
    "corporate_actions": {
      "path": "corporate_actions.csv"
    },
    "events": {
      "path": "events.csv"
    }
  }
}
```

The current production contract requires these five datasets. Provider-specific adapters may create them from multiple raw endpoints/files, but they must not inject vendor-computed StockRadar logic.

## Raw-only rule

External providers may provide raw/reference inputs such as:

- security identity and exchange;
- raw OHLCV/trades/order-book fields covered by the license;
- financial-statement line items;
- shares outstanding and raw balance-sheet/cash-flow fields;
- corporate-action facts;
- timestamped event/news facts if licensed.

The intake rejects external columns that represent StockRadar/model outputs, including examples such as:

- `score`, `rank`, `rating`, `recommendation`, `signal`;
- `ma50`, RSI/MACD/Bollinger/Ichimoku fields;
- `rvol`, VPA/VCP/stage/setup fields;
- P/E/P/B/ROE/growth metrics when supplied as derived external metrics rather than raw line items;
- fair value, MOS, Buy Zone, Stop, Target, R/R, probability or expected return.

StockRadar computes those itself from accepted raw inputs.

## Command

```bash
python scripts/intake_licensed_provider_bundle.py \
  private-staging/vendor-2026-09-04 \
  private-staging/vendor-2026-09-04/package.json \
  private-staging/vendor-2026-09-04/rights.json \
  private-staging/vendor-2026-09-04/stockradar-descriptor.json \
  private-staging/vendor-2026-09-04/intake-report.json
```

The command:

1. rejects public staging paths;
2. rejects credentials/secrets in metadata;
3. requires `LICENSED` rights and all commercial permissions;
4. checks license effective dates;
5. validates the existing StockRadar raw-input policy;
6. checks HOSE scope/path safety/coverage columns;
7. computes row counts and SHA-256 checksums through the existing production-bundle layer;
8. reports whether the package would currently pass the Production Data Gate;
9. writes no raw data to the public website;
10. changes no database/API/publication gate.

A package can be `accepted=true` but `publication_ready=false`, for example when a licensed snapshot is stale. This is intentional so reconciliation is possible without weakening publication safeguards.

## Next stage after intake

Only after `publication_ready=true` should the existing flow continue:

```text
Licensed Provider
→ private raw staging
→ Licensed Provider Intake
→ build_production_manifest.py
→ validate_production_data.py
→ StockRadar raw computations
→ report cache publication
→ explicit rights/compliance activation
→ stock_api_gate
→ website / StockRadar AI / Premium alerts
```

Activation remains a separate audited server-side action. No downloader or intake command may bypass it.

## Provider adapters

A provider-specific downloader belongs before this intake boundary and must keep credentials in environment/server secret storage. It should normalize only raw field names/formats into the package contract.

Do not implement or activate an adapter from public documentation alone. Endpoint details, entitlements, rate limits, historical scope and redistribution/display rights must match the user’s actual commercial subscription.
