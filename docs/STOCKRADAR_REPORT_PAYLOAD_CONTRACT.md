# StockRadar Decision-Grade Report Payload Contract V1

A payload may enter the authenticated production cache only when the licensed Production Data Contract has already passed and the report itself passes this contract.

## Required identity/state

Every cached report must contain:

```json
{
  "ticker": "MBB",
  "horizon": "SHORT_TERM",
  "data_status": "READY",
  "data_grade": "DECISION_GRADE",
  "current_price": 0,
  "new_position_state": "...",
  "holding_state": "...",
  "probability_calibrated": false
}
```

Rules:

- ticker is exactly three ASCII letters and must match the outer cache key;
- horizon is one of `SHORT_TERM`, `MEDIUM_TERM`, `LONG_TERM`, `ACCUMULATION` and must match the outer cache key;
- `data_status` must be `READY`;
- `data_grade` must be `DECISION_GRADE`;
- current price must be positive;
- new-position and holding states must both be present. The system does not infer one from the other.

## Optional decision fields

Supported fields include:

- `score` in 0–100;
- `setup` / `setup_type`;
- `rvol` / `volume_rvol`, non-negative;
- `buy_zone_low` + `buy_zone_high`, or a two-element `buy_zone`, both positive and ordered;
- `stop_loss`;
- `target_near` / `target_price`;
- `target_3_6m`;
- `target_12m` / `fair_value`;
- `upside_pct`, non-negative;
- `downside_pct`, signed as zero or negative;
- `risk_reward`, positive;
- `thesis`, `catalysts`, `risks`, `invalidation_conditions` as string lists.

Target and stop fields are not invented when the selected horizon does not support them. A report must preserve horizon consistency; for example a swing entry/stop must not be paired with a 12-month DCF target to manufacture Risk/Reward.

## Probability claims

`score` is not probability.

`probability_pct` is forbidden unless all of the following are present:

- `probability_calibrated=true`;
- `probability_pct` between 0 and 100;
- `probability_oos=true`;
- positive integer `probability_sample_size`;
- non-empty `probability_method`;
- non-empty `probability_scope`, describing the matching setup/regime/horizon/universe or other calibration scope.

The browser follows the same rule. If calibration evidence is absent, it displays `KHÔNG CÔNG BỐ` rather than transforming score into a win probability.

## Security

Cache publication rejects credential-shaped fields anywhere inside a report payload, including API keys, secrets, passwords, authorization values, access/refresh/service-role/trading tokens and OTP material.

## Lifecycle

A valid report payload still does not become customer-visible merely because it was cached. The authenticated API additionally requires:

- non-expired cache row;
- exact active manifest SHA-256 reference match;
- exact active snapshot ID match;
- data-rights approval;
- compliance approval;
- API safe-enable gate explicitly opened.
