# Email Architecture Contract

Status: design contract only; no production sender is connected.

## Delivery windows

| Window | Purpose | Default content |
| --- | --- | --- |
| Before session | Prepare, not predict | market state, active plans, expiries and known event risks |
| 10:30 / 11:15 / 13:30 / 14:15 | Confirmed state changes | P0 risk/invalidation, then P1 readiness/trigger |
| After session | Freeze the close | snapshot summary, new/changed/expired recommendations |
| Weekly | Review process | state transitions, immutable outcomes and method note |

These are scheduled scans, not realtime-by-the-second promises. A scan may produce no email.

## Required event

Every candidate email event contains:

- `operation_id` and deterministic `idempotency_key`;
- `recommendation_id`, `snapshot_id`, ticker and horizon;
- previous/current internal state plus approved public label;
- event priority and reason;
- Data Grade, source time, detected time and validity boundary;
- recipient preference/consent version;
- confirmation, debounce and cooldown results.

Suggested idempotency key:

`sha256(user_id | recommendation_id | snapshot_id | to_state | event_type)`

The delivery worker may retry the same operation but must never create a second user-visible alert for the same key.

## Priority and suppression

- P0: invalidation, stop, material market-regime deterioration.
- P1: enters buy zone, activation, important rank entry/exit.
- P2: thesis/fundamental event.
- P3: watch-state improvement and low-urgency digest material.

Suppress when data is MOCK/STALE/INSUFFICIENT, the state did not materially change, confirmation failed, cooldown is active, consent is missing, or the recommendation has expired/closed. P0 may bypass ordinary digest batching but never consent or data-quality gates.

## Mandatory production controls

Before enabling delivery: verified sender domain; double opt-in or documented lawful consent basis; one-click unsubscribe; suppression list; bounce/complaint handling; rate limits; encrypted secrets; minimal retention; delivery audit; provider webhook verification; disaster disable switch; and Vietnamese legal/privacy review.

GitHub Pages contains only the explanatory UI at `/email/`. It collects no email address and cannot send messages.
