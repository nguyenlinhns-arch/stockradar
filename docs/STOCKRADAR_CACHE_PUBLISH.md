# StockRadar Production Cache Publishing

This is the controlled bridge from an approved licensed-data manifest to the private Supabase stock-report cache.

## Input batch

Use a file outside the public repository, preferably named `*.stock-cache-batch.json`:

```json
{
  "contract_version": "1.0",
  "snapshot_id": "hose-provider-YYYY-MM-DD-HHMMSS-vn",
  "items": [
    {
      "ticker": "MBB",
      "horizon": "SHORT_TERM",
      "generated_at": "2026-09-03T14:16:00+07:00",
      "expires_at": "2026-09-03T15:16:00+07:00",
      "payload": {
        "ticker": "MBB",
        "horizon": "SHORT_TERM",
        "data_status": "READY",
        "data_grade": "DECISION_GRADE",
        "current_price": 30.5,
        "new_position_state": "CHỜ MUA",
        "holding_state": "THEO DÕI",
        "score": 82,
        "probability_calibrated": false,
        "thesis": ["Fundamental và cấu trúc giá cùng khung."],
        "risks": ["Luận điểm vô hiệu nếu cấu trúc kỹ thuật bị phá vỡ."]
      }
    }
  ]
}
```

The batch snapshot must match a Production Data Contract manifest that currently passes rights, coverage, freshness, corporate-action, active-status and checksum gates. Every report payload must separately pass `STOCKRADAR_REPORT_PAYLOAD_CONTRACT.md`.

## Dry run first

```bash
python scripts/publish_stock_cache.py \
  /secure/stockradar/stockradar.production-manifest.json \
  /secure/stockradar/reports.stock-cache-batch.json
```

A successful dry run prints only record count and the SHA-256 manifest reference. It does not print report payloads or credentials.

Validation blocks:

- stale/non-publishable production manifest;
- snapshot mismatch;
- invalid ticker or horizon;
- duplicate ticker/horizon records;
- report generated before the source snapshot;
- invalid expiry window;
- payload ticker/horizon mismatch;
- any report that is not `READY + DECISION_GRADE`;
- missing positive current price;
- missing independent new-position or holding state;
- invalid score/RVOL/Buy Zone/Stop/Target/Upside/Downside/Risk-Reward fields;
- uncalibrated probability claims;
- calibrated probability without OOS flag, sample size, method and calibration scope;
- credential-shaped fields such as API keys, passwords, access/refresh/service-role/trading tokens or OTP.

`score` is never treated as win probability. If a report has no valid calibration evidence, leave `probability_calibrated=false` and omit `probability_pct`; the customer UI will show `KHÔNG CÔNG BỐ`.

## Publish

Set secrets only in the server/worker environment:

```bash
export SUPABASE_URL='https://<project>.supabase.co'
export SUPABASE_SERVICE_ROLE_KEY='...'
python scripts/publish_stock_cache.py \
  /secure/stockradar/stockradar.production-manifest.json \
  /secure/stockradar/reports.stock-cache-batch.json \
  --publish
```

There is deliberately no CLI argument for the service-role key, reducing the chance of leaking it through shell history/process listings.

The publisher calls the service-role-only RPC `upsert_stockradar_cached_report`. Browser roles cannot call that RPC.

## Manifest binding

The exact production manifest file is hashed as `sha256:<digest>` and stored with every cache row. `private.stock_api_gate` separately records the approved `active_manifest_ref` and `active_snapshot_id`.

Even when the API is later enabled, the fetch RPC returns `BLOCKED_DATA_GATE / CACHE_MANIFEST_MISMATCH` unless both values on a report match the active gate. Expired reports return `REPORT_STALE`.

## Enabling production API

Cache publication does **not** enable the API. `api_enabled` remains false until all of these are true and explicitly recorded:

- `data_ready=true`;
- `data_rights_approved=true`;
- `compliance_approved=true`;
- evidence reference present;
- active manifest reference present;
- active snapshot ID present.

This separation prevents successful ingestion from being mistaken for legal/compliance approval to serve customer-facing data.
