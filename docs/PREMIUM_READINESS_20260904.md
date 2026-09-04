# StockRadar Premium Readiness — 2026-09-04

## Commercial gate

Paid checkout must remain disabled until all of the following are true in production:

- Decision-grade market data is ready and approved for use.
- Stock API release gate is enabled.
- A current production manifest and snapshot are active.
- Stock report cache contains real HOSE reports.
- Radar/recommendation/today-changes feeds are generated from that production snapshot.
- Email delivery gate is production-ready and a real Action Alert test succeeds.
- One end-to-end paid test account completes signup -> verify -> checkout approval -> PAID -> AI/report -> watchlist -> alert -> email -> expiry path.

Current production action on 2026-09-04: `private.billing_gate.checkout_enabled = false` with evidence `PAUSED_2026-09-04_UNTIL_DECISION_FEED_READY`.

## Paid information architecture

Primary paid navigation:

1. StockRadar AI
2. Hôm nay
3. My StockRadar
4. Radar
5. Hiệu quả

Legacy duplicate/obsolete routes should redirect:

- `/pro/` -> `/dang-ky/`
- `/email/` -> `/tai-khoan/`
- `/theo-doi/` -> `/tai-khoan/`
- `/phan-tich/` -> `/kiem-tra-co-phieu/`

## Product tiers

Use only `FREE` and `PREMIUM` in customer-facing copy.

Guest: 3 AI questions/day.
Free: 10 AI questions/day; basic watchlist; system/account emails only.
Premium: unlimited AI; full decision layer; larger watchlist; Daily 09:00 and Action Alert when delivery gate is ready.

## Private position context

`watchlist_items.average_cost` and `watchlist_items.portfolio_weight_pct` are optional user-supplied fields for private AI position/risk context. They must never be exposed through public feeds or other users' email.
