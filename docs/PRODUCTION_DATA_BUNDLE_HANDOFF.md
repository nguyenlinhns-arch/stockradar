# StockRadar Licensed Production Bundle Handoff V1

This document defines the provider-neutral handoff StockRadar accepts from an approved market-data supplier. It is intentionally independent of any one API/vendor.

## Do not commit licensed data

Licensed payloads, API credentials, provider tokens and generated production manifests stay outside the public GitHub repository. `.gitignore` blocks the standard production-data directories and manifest names, but operators remain responsible for secure storage.

## Required bundle

Place the following CSV files in one secure local/server directory:

1. `security_master.csv`
2. `ohlcv.csv`
3. `fundamentals.csv`
4. `corporate_actions.csv`
5. `events.csv`

The first three must contain a canonical three-letter `ticker` column or the descriptor must name the provider's equivalent column. Corporate-actions/events files may contain only headers when there are no rows for the snapshot.

The production adapter is HOSE-only. HNX/UPCoM rows must not be supplied in the StockRadar bundle.

## Descriptor

Keep a descriptor JSON beside the secure bundle. The descriptor contains no credentials. Minimum shape:

```json
{
  "contract_version": "1.0",
  "snapshot": {
    "snapshot_id": "hose-provider-YYYY-MM-DD-HHMMSS-vn",
    "as_of": "2026-09-03T14:15:00+07:00",
    "source_timestamp": "2026-09-03T14:15:00+07:00",
    "exchange": "HOSE",
    "expected_total": 0,
    "scanned_count": 0,
    "valid_count": 0,
    "excluded_count": 0,
    "stale_count": 0,
    "missing_count": 0,
    "data_grade": "DECISION_GRADE",
    "same_snapshot": true,
    "adjusted_basis_consistent": true,
    "corporate_action_checked": true,
    "source": "LICENSED_PROVIDER",
    "exclusion_log": []
  },
  "rights": {
    "publication_allowed": false,
    "redistribution_allowed": false,
    "source_terms_reviewed": false,
    "evidence_ref": ""
  },
  "active_status": {
    "semantics_resolved": false,
    "market_status_checked": false
  },
  "datasets": {
    "security_master": {"path": "security_master.csv", "ticker_column": "ticker"},
    "ohlcv": {"path": "ohlcv.csv", "ticker_column": "ticker"},
    "fundamentals": {"path": "fundamentals.csv", "ticker_column": "ticker"},
    "corporate_actions": {"path": "corporate_actions.csv"},
    "events": {"path": "events.csv"}
  }
}
```

The example is deliberately blocked. Rights flags may become true only after written approval is recorded.

## Assembly

```bash
python scripts/build_production_manifest.py \
  /secure/stockradar/bundle \
  /secure/stockradar/bundle/descriptor.json \
  /secure/stockradar/stockradar.production-manifest.json
```

The assembler:

- rejects paths escaping the secure bundle directory;
- accepts CSV only in V1;
- validates canonical three-letter ticker values for coverage datasets;
- streams SHA-256 calculation rather than loading large data files into memory;
- counts rows and unique covered tickers;
- attaches every dataset to the same snapshot ID;
- passes the result through the Production Data Gate.

By default, a blocked manifest is not written. `--allow-blocked` may be used for internal rights/reconciliation review only; the command still returns a blocked exit status.

## Publication

A successful manifest alone does not publish raw vendor files. It only authorizes the later production build to consume a validated snapshot. GitHub Pages refuses production-looking public payloads unless `STOCKRADAR_PRODUCTION_MANIFEST` points to a fresh manifest that passes the full contract.

## Intraday StockRadar snapshots

For the official 10:30, 11:15, 13:30 and 14:15 scans, use a new immutable snapshot ID and source timestamp per checkpoint. Do not overwrite an earlier checkpoint and call it the same snapshot. Intraday volume must preserve the true observation time so RVOL/same-time calculations are not confused with full-day volume.
