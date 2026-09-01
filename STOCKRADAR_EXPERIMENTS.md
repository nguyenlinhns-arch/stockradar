# STOCKRADAR EXPERIMENT LOG

This log is append-only. Failed experiments remain visible. Metrics are blank until real Ads and product events exist.

## EXP-001 — Radar 5 acquisition

- `experiment_id`: EXP-001
- `hypothesis`: A five-setup promise reduces market-search overload and produces the lowest cost per activated user.
- `proposition`: RADAR5
- `audience`: Same broad Vietnam audience used for all propositions; final eligibility subject to Meta policy review.
- `creative`: R5-A, R5-B
- `landing_page`: `/radar5`
- `budget`: 150.000đ/day for 7 days (1.050.000đ media; tax handled separately)
- `start_date`: TBD
- `end_date`: TBD
- `impressions`: —
- `clicks`: —
- `signups`: —
- `activation`: —
- `retention_d1`: —
- `retention_d7`: —
- `pro_intent`: —
- `paid`: —
- `result`: NOT_STARTED
- `decision`: Wait for Ads access, policy verification, production landing and event QA.

## EXP-002 — Breakout timing

- `experiment_id`: EXP-002
- `hypothesis`: “Before breakout / not extended” creates higher alert opt-in and return behavior than a generic shortlist.
- `proposition`: BREAKOUT
- `audience`: Same audience/placements as EXP-001.
- `creative`: BO-A, BO-B
- `landing_page`: `/breakout`
- `budget`: 150.000đ/day for 7 days (1.050.000đ media; tax handled separately)
- `start_date`: TBD
- `end_date`: TBD
- `impressions`: —
- `clicks`: —
- `signups`: —
- `activation`: —
- `retention_d1`: —
- `retention_d7`: —
- `pro_intent`: —
- `paid`: —
- `result`: NOT_STARTED
- `decision`: Same launch gates as EXP-001.

## EXP-003 — Risk retention

- `experiment_id`: EXP-003
- `hypothesis`: Invalidation/stale-signal monitoring produces the strongest D7 retention and PRO intent.
- `proposition`: RISK
- `audience`: Same audience/placements as EXP-001.
- `creative`: RR-A, RR-B
- `landing_page`: `/risk`
- `budget`: 150.000đ/day for 7 days (1.050.000đ media; tax handled separately)
- `start_date`: TBD
- `end_date`: TBD
- `impressions`: —
- `clicks`: —
- `signups`: —
- `activation`: —
- `retention_d1`: —
- `retention_d7`: —
- `pro_intent`: —
- `paid`: —
- `result`: NOT_STARTED
- `decision`: Same launch gates as EXP-001.

## Winner rule

Do not declare a winner at the end of the 7-day media run. D7 requires a further observation window. Compare propositions on:

1. Cost per activated user.
2. D1 and D7 retention.
3. Alert opt-in.
4. PRO intent.
5. Qualitative feedback.
6. Paid conversion/CAC only after payment is legitimately enabled.

If samples are too small, extend the same experiment; do not manufacture certainty from CTR.

