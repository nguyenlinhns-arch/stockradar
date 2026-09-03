# Email Architecture Contract

Status: design contract only; no production sender is connected.

## Entitlement gate

Transactional mail is available where required for every account tier. Product content (`daily`, `state_change`, `post_session`, `weekly`) is eligible only for verified, consented Trial/Paid accounts. Free accounts are always suppressed for product content even if an obsolete opt-in flag exists. Paid content is ordered by watchlist ticker, preferred horizon and sector before general items.

## Delivery windows

| Window | Purpose | Default content |
| --- | --- | --- |
| 09:00 Vietnam time | Daily pre-session report | explicit report date/data cutoff, market state, objective Top 5 HOSE, objective sector Top 5, existing lifecycle changes and known event risks |
| 10:30 / 11:15 / 13:30 / 14:15 | Confirmed state changes | P0 risk/invalidation, then P1 readiness/trigger |
| After session | Freeze the close | snapshot summary, new/changed/expired recommendations |
| Weekly | Review process | state transitions, immutable outcomes and method note |

These are scheduled scans, not realtime-by-the-second promises. A scan may produce no email.

## Date and freshness contract

Every product email carries separate fields for:

- `report_date`: Vietnam calendar date of the email/report;
- `market_session_reference`: trading session represented by the primary market data;
- `data_cutoff_at`: latest verified source/snapshot time or strongest verified session boundary;
- `generated_at`: generation time in Vietnam time.

The daily subject must include `report_date`, for example:

`[StockRadar][dd/mm/yyyy] Báo cáo thị trường hàng ngày`

At 09:00, the latest verified data may still be from the previous trading session. In that case the email must show both dates explicitly and must not label the older snapshot as current-day market data.

For in-session action alerts, use the Vietnam signal date in the subject, for example:

- `[CHỨNG KHOÁN][dd/mm/yyyy] ĐẠT ĐIỂM MUA – <MÃ>`
- `[CHỨNG KHOÁN][dd/mm/yyyy] CẢNH BÁO BÁN – <MÃ>`

Corrections preserve the original report date but prepend `[CẬP NHẬT]` or `[ĐÍNH CHÍNH]` and expose the new generation/data cutoff time.

## Required event

Every candidate email event contains:

- `operation_id` and deterministic `idempotency_key`;
- `recommendation_id`, `snapshot_id`, ticker and horizon;
- previous/current internal state plus approved public label;
- event priority and reason;
- Data Grade, source time, detected time and validity boundary;
- `report_date`, `market_session_reference`, `data_cutoff_at`, `generated_at`;
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

## Highest-tier internal delivery

The internal/admin highest-tier group is:

- `nguyenlinhns@gmail.com`
- `Anh.le2910@gmail.com`
- `phuonghan666@gmail.com`
- `leanhtkv@gmail.com`

All four receive the same highest available Premium report/alert version when delivery is permitted by the production security gate. This group is internal-only metadata and must not appear in public/customer-facing content.

## Mandatory production controls

Before enabling delivery: verified sender domain; double opt-in or documented lawful consent basis; one-click unsubscribe; suppression list; bounce/complaint handling; rate limits; encrypted secrets; minimal retention; delivery audit; provider webhook verification; disaster disable switch; and Vietnamese legal/privacy review.

GitHub Pages contains only the explanatory UI at `/email/`. It collects no email address and cannot send messages.
