# STOCKRADAR PRODUCT SPEC V1

Version: 1.0  
Status: implemented as local MVP with MOCK-labelled data  
Brand: **STOCKRADAR** / **stockradar.vn**

## 1. Product outcome

StockRadar solves one job:

> Quét HOSE → chắt lọc rất ít setup đáng theo dõi → báo khi trạng thái thay đổi.

Core proposition:

> Không cần xem hàng trăm cổ phiếu. StockRadar đã lọc trước.

V1 is an experiment vehicle, not a terminal. Its purpose is to learn which narrow value proposition produces activated users, retention and willingness to pay.

## 2. V1 scope

Included:

1. Home.
2. Radar 5.
3. Breakout Radar.
4. Risk Radar.
5. Immutable Track Record.
6. FREE/PRO explanation and lead capture.
7. State-change alert contract.
8. Minimum ranking engine.
9. Analytics/UTM contract.
10. Ads experiment kit.

Excluded until evidence justifies expansion:

- price board, charting terminal, newsfeed or financial-statement warehouse;
- custom screener builder;
- social network;
- native mobile app;
- personalized portfolio management;
- broker integration or order placement;
- uncalibrated price prediction.

## 3. Three propositions

| Proposition | Job | Primary hypothesis | Landing |
| --- | --- | --- | --- |
| StockRadar 5 | Reduce search overload | A short ranked list creates acquisition | `/radar5` |
| Breakout Radar | Improve timing | Users want to see setups before they become extended | `/breakout` |
| Risk Radar | Reduce stale-signal risk | State deterioration creates retention and willingness to pay | `/risk` |

No proposition is declared the winner before D7 retention and PRO intent are observed.

## 4. User-facing states

- `WATCH`
- `NEAR_TRIGGER`
- `READY`
- `TRIGGERED`
- `INVALIDATED`
- `EXTENDED`
- `EXPIRED`

State changes are first-class product events. High-value transitions include:

- `WATCH → NEAR_TRIGGER`
- `NEAR_TRIGGER → READY`
- `READY → TRIGGERED`
- `READY → INVALIDATED`
- `TRIGGERED → EXTENDED`
- `TOP5 → OUT_OF_TOP5`
- `OUTSIDE_TOP5 → TOP5`

Impossible resurrection paths, such as `INVALIDATED → READY`, are rejected. A new setup requires a new setup identity/snapshot lineage.

## 5. Radar 5 publishing gate

The label `TOP5_HOSE` is allowed only when all conditions pass:

1. Exchange is HOSE.
2. Expected universe is known.
3. Scanned count equals expected universe.
4. `valid + excluded = expected`.
5. Exclusion log reconciles.
6. Missing/stale counts are zero for required fields.
7. Same-snapshot and adjusted-basis checks pass.
8. Corporate actions are checked.
9. Data Grade is `DECISION_GRADE`.
10. At least five eligible setups exist.

Otherwise output is exactly one of:

- `INCOMPLETE_UNIVERSE`
- `SHORTLIST_FROM_AVAILABLE_DATA`

MOCK data can never publish `TOP5_HOSE`.

## 6. Score contract

Weights are fixed for V1:

| Bucket | Weight |
| --- | ---: |
| Trend / structure | 20 |
| Volume / VPA | 15 |
| SEPA + CANSLIM setup | 20 |
| Relative Strength | 10 |
| Fundamental | 15 |
| Valuation | 10 |
| Catalyst | 5 |
| Risk / liquidity | 5 |

Rules:

- Score is evidence quality, not win probability.
- Exact score is shown only at 100% score Coverage; otherwise show a range.
- Missing evidence is not treated as zero and score is not renormalized.
- The same evidence ID cannot receive full credit in multiple buckets.
- Ranking compares candidates from the same snapshot/basis/framework.

## 7. Candidate eligibility

Radar 5 candidates must have:

- state in `WATCH`, `NEAR_TRIGGER`, `READY` or `TRIGGERED`;
- score Coverage 100%;
- liquidity gate PASS;
- event-risk gate PASS;
- no `INVALIDATED`, `EXTENDED` or `EXPIRED` state.

Market Regime does not silently change score. It changes action/priority and may block new entries.

## 8. Track Record

At publication, freeze:

- snapshot ID/time/source;
- universe reconciliation/Coverage/Data Grade;
- ticker, rank, score, setup and state;
- Market Regime;
- evidence, current price and pivot;
- reason and state change.

Original snapshots and entries are immutable. Later performance is appended as observations containing horizon, outcome, MAE, MFE and R-multiple. Errors create correction records; they never overwrite the original release.

## 9. FREE / PRO

FREE:

- Radar 5 after session;
- Market Regime, score and state;
- public Track Record;
- basic weekly summary.

PRO price experiment: **199.000–299.000đ/month**, not yet a live price.

PRO hypothesis:

- earlier Radar;
- state-change alerts;
- entry/exit from Radar 5;
- READY / INVALIDATED / Market alerts;
- Risk Radar and deeper history.

No payment is enabled before data, compliance, privacy and subscription gates pass.

## 10. Alert contract

Alert priority:

- P0 — risk/invalidation/market regime.
- P1 — entry readiness/trigger.
- P2 — thesis/fundamental event.
- P3 — watch-state improvement.

An alert is not an automatic buy/sell instruction. Each action-oriented alert must carry snapshot, timestamp, state change, reason, Data Grade and validity boundary.

## 11. Success metrics

Primary:

1. Cost per activated user.
2. D1 retention.
3. D7 retention.
4. Alert opt-in.
5. PRO intent.
6. Paid conversion, once legally and technically enabled.
7. CAC feasibility.

CTR and likes are diagnostic, not winner metrics.

## 12. V1 acceptance criteria

Local MVP passes when:

- rules engine and ledger tests pass;
- MOCK is visible and blocked from Top 5 claims;
- all six pages render on desktop/mobile;
- signup and analytics endpoints work locally;
- 6 creatives exist in 4:5 and 9:16;
- campaign and event schemas are complete;
- blockers are explicit.

Production V1 additionally requires:

- licensed/current HOSE data and full-universe reconciliation;
- real scheduler/alert delivery;
- deployed hosting, domain/DNS and TLS;
- privacy/consent operations;
- formal Vietnamese legal/compliance review;
- Meta financial-ad eligibility/verification where required;
- at least one complete production snapshot through the shipping gate.

