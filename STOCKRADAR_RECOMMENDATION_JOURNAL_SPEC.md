# StockRadar Recommendation Journal Specification V2.1.2

## Purpose

The journal explains what changed, when, why and under which system/snapshot so recommendation history cannot be rewritten after the outcome is known.

## Required event contract

`event_id`, `recommendation_id`, `timestamp`, `previous_state`, `new_state`, `event_type`, `old_value`, `new_value`, `reason`, `snapshot_id`, `system_version`, `created_by`, `audit_reference`, optional `correction_of`.

Supported events include WATCHED, WAIT_BUY, PUBLISHED, ACTIVATED, OBSERVED, SCORE_CHANGED, TARGET_CHANGED, REVIEWED, TARGET_REACHED, STOP_REACHED, INVALIDATED, EXPIRED, CLOSED and CORRECTION.

## Review schedule

Every recommendation has `review_due_at`. Missing due time is treated as due immediately. Review yields CONTINUE, ADJUST, NO_LONGER_ELIGIBLE or CLOSE and appends a REVIEWED event. Recommendations do not remain open indefinitely.

## Immutability

Update/delete triggers reject recommendation-event mutation. Corrections are new events with actor, reason, audit reference and pointer to the original. Public UI may summarize events but must preserve event ordering and expose the audit reference.
