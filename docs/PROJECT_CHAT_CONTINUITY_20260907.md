# Project chat continuity — 2026-09-07

## Verified starting point

The previous private bridge Pages run `34072504216` completed successfully, including multi-viewport browser QA and deployment. The linked owner conversation and reviewed handoff remain in the existing private database; they are not recreated or published by this change.

## Scope

The browser previously used one unowned localStorage thread pointer and copied authenticated history into the same buffer that Guest requests used. Server ownership checks blocked direct cross-account reads, but the UI still needed explicit account/session isolation, stale-response rejection and safe recovery of invalid saved pointers.

This repair scopes the pointer to the signed-in account, removes the legacy unowned pointer, clears displayed history on account transitions, and rejects late responses from previous sessions or superseded history requests. Authenticated history remains server-side and is never placed in the Guest buffer. An explicit failed sidebar selection does not silently move the user to another conversation; only initial restoration can recover a missing pointer once through owned server history.

The existing `Tiếp tục từ dự án` control opens the linked conversation without inference. The status distinguishes an opened project conversation from a successful model reply. Imported project summaries are visibly labelled as reviewed handoffs, not verbatim user messages. A token refresh for the same account no longer forces history hydration over the current conversation.

No provider configuration, API key, quota, entitlement, payment, email gate, data gate or market-analysis rule is changed. No new external synchronization service is introduced. ChatGPT Project messages are still transferred as explicit reviewed handoffs, and website history is read through the authorized connector on request.

## Verification

Fifteen synthetic client-behavior cases execute the real browser source in an isolated VM: account-scoped storage, logout cleanup, summary labelling, Guest isolation, delayed history/list/model/new-thread/resume responses, same-account reauthentication, out-of-order history, pointer recovery and token-refresh behavior. The feature workflow also runs the existing Node/Python and bridge suites before committing the repaired client.

At source preparation, new feature verification and deployment are pending. Record the actual results after the workflow and live-asset checks; do not infer a successful live authenticated model conversation from synthetic tests.
