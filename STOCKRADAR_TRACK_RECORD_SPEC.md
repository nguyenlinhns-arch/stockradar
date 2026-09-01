# StockRadar Track Record Specification V2.1.2

## Purpose

Preserve exactly what was known, published, activated and closed so product claims can be reproduced without hindsight.

## Modes

- `BACKTEST`: historical simulation with explicit dataset and as-of controls.
- `SHADOW`: forward-running record not offered as a production recommendation.
- `LIVE_PUBLISHED`: genuinely published after all production gates passed.

Never relabel or backfill BACKTEST/SHADOW as LIVE_PUBLISHED.

## Append-only entities

Snapshot, radar output, recommendation, recommendation event, review schedule, corporate action, benchmark record, manual override, ticker event and correction. SQL implementation is in `track-record/schema.sql`; updates/deletes of protected history are rejected.

## Public aggregates

Always show record mode, period, horizons, publication/activation dates, entry, current-or-close price, total published, unactivated, open, closed, wins/losses, win-rate denominator, average/median return where sample permits, VN-Index/excess return, corporate-action basis and correction count. Public history includes winners and losers; no cherry-picking.

## Reproduction

Each recommendation must resolve to snapshot ID, source timestamps, system/score version, evidence IDs, publication/activation/review/close events, adjustment basis and matching-window benchmark records. Manual intervention requires a named actor, reason and audit reference.
