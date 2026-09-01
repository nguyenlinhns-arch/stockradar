# StockRadar Track Record Specification V2

## Purpose

Preserve exactly what was known, published, activated and closed so product claims can be reproduced without hindsight.

## Modes

- `BACKTEST`: historical simulation with explicit dataset and as-of controls.
- `SHADOW`: forward-running record not offered as a production recommendation.
- `LIVE_PUBLISHED`: genuinely published after all production gates passed.

Never relabel or backfill BACKTEST/SHADOW as LIVE_PUBLISHED.

## Append-only entities

Snapshot, radar output, recommendation, recommendation event, corporate action, benchmark observation, manual override and correction. SQL implementation is in `track-record/schema.sql`; updates/deletes of protected records are rejected.

## Public aggregates

Always show record mode, period, horizons, total published, unactivated, open, closed, wins/losses, win-rate denominator, average/median return where sample permits, benchmark/excess return, corporate-action basis and correction count. Suppress/invalidate a metric when its denominator or rights/source is unresolved.

## Reproduction

Each recommendation must resolve to snapshot ID, source timestamps, system/score version, evidence IDs, publication and activation events, adjustment basis and benchmark observations. Manual intervention requires a named actor and reason.
