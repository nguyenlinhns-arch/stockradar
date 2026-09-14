# StockRadar Project queue recovery — 15 September 2026

## Applied change
The live database migration `20260914222206_project_queue_claim_recovery` is applied.
The native widget remains version 0.4.0 (Edge deployment 8); this is a database-side
reliability update and does not require reinstalling anything on a PC.

`stockradar_native_probe_signal()` and `read_stockradar_project_inbox()` now both
require an enabled owner route, an ACTIVE matching thread, WEBSITE origin, a WAITING
or PROCESSING state, and no active unexpired claim. Expired claims and missing-claim
PROCESSING rows can therefore be discovered for recovery. Cancellation, completed
answers and verification fixtures do not cause native wakeups or consume inbox slots.
The native signal additionally retains its existing enabled bridge-capability gate.
The inbox remains usable by the already authorized manual Project processor.

No claim/completion function, account, payment, entitlement, database grant, email,
trading, publication or OpenAI inference configuration was changed. The signal still
returns only its existing boolean and version, not private content or request IDs.

## Measured results
All times in this section are Asia/Bangkok (UTC+7).

- At 05:21:52, a labelled rollback-only fixture reproduced the original bug:
  the expired PROCESSING question appeared in the inbox but pending was false.
- After migration, the trusted-database integration suite passed 14/14 cases at
  05:22:39: waiting visibility, active-claim exclusion, double-claim rejection,
  expired-claim recovery, stale-token rejection, missing-claim recovery, live-claim
  exclusion even with WAITING status, verification-record filtering, matching answer
  and thread body, completed-record filtering, idempotent delivery, overwrite
  rejection, cancelled-request rejection, and unchanged browser execution denial.
- At 05:23:12, readback found zero leftover test questions and zero leftover test
  messages. The original record counts were unchanged. Grants on both functions
  remained limited to postgres/service_role. The real inbox was empty.
- `node --test tests/native_bridge_v4.test.mjs` was rerun locally: 19/19 passed.
  This is a mocked-host/controller suite, not a real ChatGPT/browser end-to-end test.

The SQL suite creates explicitly labelled synthetic fixtures only inside a rollback
subtransaction, including the answer-to-thread trigger. The fixture user/thread are
resolved from the existing authorized route, not hardcoded. No real pending question
is claimed, no auth token is fabricated, and no private IDs or claim tokens are
returned in its report. The test refuses to proceed when eligible live work exists.
Postgres identity sequences may advance even when fixture rows are rolled back.

Run the SQL suite only through a trusted administrator connection. It is not a
browser-accessible processor endpoint. Its passing result is database integration
evidence, not a newly delivered real website answer.

## Evidence boundaries
The owner's prior explicit native-card check produced a message in this same Project
conversation. That verifies the card-to-conversation leg for that check, not an
always-running worker. Read-only inspection of an existing WEBSITE answer dated
12 September found two linked history messages and an exact stored answer match;
it does not establish a new live browser round trip on 15 September.

The Opera browser connector was disconnected in this turn. No new website question
was submitted from a logged-in browser, and no rendered website answer was observed.
Do not describe this release as fully verified unattended website AI or native
synchronization of every Project message. The card still requires explicit activation
and host retention; it can pause when hidden or disappear when unloaded. Its boolean
latch still deliberately avoids repeated dispatch while pending stays continuously
positive; a manual check may be needed for an uninterrupted backlog.

## Source and rollback
Source migration: `supabase/migrations/20260914222206_project_queue_claim_recovery.sql`.
Transactional tests: `tests/sql/project_queue_claim_recovery.sql`.
The change only replaces two functions; existing claim/completion and privacy gates
remain authoritative. Reverting requires a reviewed migration restoring the previous
function definitions, not changing accounts, grants or clearing real questions.

Official host-interface reference: https://developers.openai.com/plugins/build/chatgpt-ui
Official database-test reference: https://supabase.com/docs/guides/database/testing
