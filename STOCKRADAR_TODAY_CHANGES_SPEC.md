# StockRadar Today Changes Specification V2.1.2

## Job

Answer “what is meaningfully different from the prior eligible snapshot?” in 30–60 seconds. This is a compact diff, not a newsfeed.

## Included changes

New/removed Top item; material score change; public-state change; new/cancelled recommendation; activation; extended above buy zone; target/stop/invalidation/close; Market Regime change. Each item carries event ID, ticker when applicable, event type, time, previous/new value, summary, importance, snapshot and mode.

## Excluded noise

Small price ticks, repeated identical observations, user clicks, low-confidence changes, general news and generated filler. If nothing passes the significance threshold, the view says there is no material change.

## Integrity

The view derives from append-only events, honors the same data grade/freshness rules and shows MOCK/SHADOW/production mode. A correction is visible as a correction; an old event is never silently edited.
