# StockRadar Performance Methodology V2.1.2

## Eligible sample

Report counts for total published, unactivated, open and closed separately. Win rate and average closed return use only closed, activated records. Unactivated records are neither wins nor losses; open records are not included in final win rate.

## Returns

For an open record: `current_return = current_price / performance_entry_price - 1`.

For a closed record: `final_return = adjusted_close_price / adjusted_entry_price - 1`, plus verified cash distributions only when reporting total return.

`excess_return = recommendation_return - benchmark_return` over matching timestamps and adjustment basis.

## Corporate actions

Splits and stock dividends adjust price/share factors. Verified cash dividends are excluded from Price Return and included in Total Return. Rights issues, mergers, delistings or ambiguous actions block the calculation until resolved. Every action has an effective time, source reference and processing status.

## Benchmark

Default benchmark for HOSE recommendations is VN-Index, using the index at activation and at the same current/close timestamp as the recommendation. `benchmark_return = current_or_close_value / start_value - 1`; `excess_return = recommendation_return - benchmark_return`. Sector benchmark is optional but must use the same window and adjusted basis. The provider and redistribution right must be approved before public production use.

## Anti-bias rules

- no best intraday fill, hindsight window or survivorship-only universe;
- no backfilled history labeled live;
- segment BACKTEST, SHADOW and LIVE_PUBLISHED;
- show sample size and inclusion/exclusion rules;
- freeze closed outcomes and append corrections;
- distinguish price return from total return.

The current website dataset is MOCK/SHADOW and demonstrates calculations only; it is not evidence of investment performance.
