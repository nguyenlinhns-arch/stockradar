# StockRadar Recommendation Schema V2.1.2

Canonical machine contract: `engine/schemas/recommendation-record.schema.json`.

## Identity and audit

`recommendation_id`, `ticker`, `horizon`, `snapshot_id`, `generated_at`, `published_at`, `system_version`, `score_version`, `publish_status`, `record_mode`, `data_grade`, `is_mock`.

## Three price concepts

| Field | Meaning | Mutability |
| --- | --- | --- |
| `price_at_publication` | observed price when the record was published | immutable |
| `recommended_buy_low/high` | conditional buy zone frozen before outcome | immutable |
| `performance_entry_price` | deterministic first eligible post-publication zone touch | null until activation, then immutable |

Current price is a new observation. It never replaces any of the three fields.

## Lifecycle and performance

`recommendation_state`, `activation_timestamp`, `current_return_pct`, `absolute_return`, `close_price`, `close_timestamp`, `final_return_pct`, `close_reason`, `benchmark_return_pct`, `sector_benchmark_return_pct`, `excess_return_pct`, `adjustment_basis`, `corporate_action_refs`.

## V2.1 review, position and benchmark fields

`review_due_at`, `review_status`, `review_decision`, `new_position_state`, `new_position_note`, `holding_state`, `holding_note`, `vnindex_at_activation`, `vnindex_current_or_close`.

`recommendation_events` requires event ID, recommendation ID, timestamp, previous/new state, event type, old/new value, reason, snapshot ID, system version, creator and audit reference. An error is fixed only by an appended `CORRECTION` that points to the prior event.

## Required invariants

- `UNACTIVATED`: activation, entry, current return and final return are null.
- Open and activated: entry exists; current return may be calculated; close/final fields are null.
- Closed: close price/time/final return exist; current return is null and never revised by later prices.
- Short/medium actionable records require horizon-consistent entry, target and stop/invalidation plus qualified R:R.
- Long/accumulation do not receive a synthetic short-term stop.
- Every material change is an append-only event or correction, never an in-place historical rewrite.
- Every open recommendation has a review deadline. Missing deadline is due immediately; the review decision is CONTINUE, ADJUST, NO_LONGER_ELIGIBLE or CLOSE.
- New-position and holding conclusions are independent. EXTENDED may be `KHÔNG MUA ĐUỔI` while an intact holding thesis remains `TIẾP TỤC THEO DÕI`.
- `BACKTEST`, `SHADOW` and `LIVE_PUBLISHED` may not be merged in public statistics without explicit segmentation.
