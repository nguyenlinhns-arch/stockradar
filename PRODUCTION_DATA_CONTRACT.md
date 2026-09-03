# StockRadar Production Data Contract V1

Purpose: define the minimum machine-verifiable contract required before StockRadar may publish real HOSE market data, full-universe rankings or production recommendations.

The default public build remains fail-closed. A production-looking Pages payload is rejected unless `STOCKRADAR_PRODUCTION_MANIFEST` points to a manifest that passes this contract.

## Required manifest structure

```json
{
  "contract_version": "1.0",
  "snapshot": {
    "snapshot_id": "...",
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
    "security_master": {
      "present": false,
      "snapshot_id": "...",
      "as_of": "...",
      "sha256": "...",
      "row_count": 0,
      "covered_tickers": 0
    },
    "ohlcv": {
      "present": false,
      "snapshot_id": "...",
      "as_of": "...",
      "sha256": "...",
      "row_count": 0,
      "covered_tickers": 0
    },
    "fundamentals": {
      "present": false,
      "snapshot_id": "...",
      "as_of": "...",
      "sha256": "...",
      "row_count": 0,
      "covered_tickers": 0
    },
    "corporate_actions": {
      "present": false,
      "snapshot_id": "...",
      "as_of": "...",
      "sha256": "...",
      "row_count": 0
    },
    "events": {
      "present": false,
      "snapshot_id": "...",
      "as_of": "...",
      "sha256": "...",
      "row_count": 0
    }
  }
}
```

The template above is intentionally non-publishable. Do not set rights flags to true without written evidence.

## Hard gates

A production manifest passes only when all of the following are true:

- Exchange is HOSE.
- `scanned_count == expected_total`.
- `valid_count + excluded_count == expected_total` and the exclusion log is complete.
- No stale or missing records are present.
- All inputs share one snapshot and use a consistent adjusted-price basis.
- Corporate actions have been checked.
- Data grade is `DECISION_GRADE`.
- Snapshot/source timestamps are timezone-aware and within the configured freshness limit.
- Active/tradable status semantics are resolved and the current market status has been checked.
- Publication, redistribution and source-terms review are explicitly approved with an evidence reference.
- Security master, OHLCV, fundamentals, corporate actions and events are present, checksummed and tied to the same snapshot.
- Security master covers the expected HOSE universe; OHLCV and fundamentals cover all valid tickers.
- No credential-shaped fields such as API keys, passwords, authorization values, access/refresh/trading tokens or OTP material exist anywhere in the manifest.

## Validation

Manual/CI validation:

```bash
python scripts/validate_production_data.py /secure/path/production-manifest.json --max-age-hours 6
```

Exit code `0` means the manifest passes. Exit code `2` means publication remains blocked.

GitHub Pages publication behavior:

- Fail-closed `BLOCKED_DATA_GATE` payloads build without a production manifest.
- If any public payload claims real/unblocked data, `full_universe=true`, `is_top5_hose=true` or `recommendation_mode=PRODUCTION_APPROVED`, the Pages build requires `STOCKRADAR_PRODUCTION_MANIFEST`.
- Payload snapshot IDs must match the validated manifest snapshot.
- If any gate fails, deployment stops before the Pages artifact is uploaded.

## StockRadar source separation

- Private/internal engines may use sources whose contracts allow owner-only analysis.
- Customer/public surfaces require explicit public display, redistribution and derived-data rights.
- A technically usable API is not automatically a legally publishable source.
- DNSE LightSpeed Market Data currently remains internal-only for StockRadar public-product purposes unless written redistribution approval is obtained; see `STOCKRADAR_DATA_RIGHTS.md`.
