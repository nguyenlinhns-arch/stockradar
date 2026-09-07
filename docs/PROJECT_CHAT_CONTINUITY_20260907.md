# Project chat continuity — released 2026-09-07

## Release outcome

Account/session-safe conversation continuity is implemented and published from source commit `12603ba673a57b3aecffdae0cf517eb83fe710ed`. Feature verification run `34073599794` completed successfully before merge. Pages run `34073650993` subsequently completed with both build and deploy marked success, including multi-viewport browser QA. This is a browser continuity repair; backend AI functions, provider configuration, account rights and market-analysis logic were not changed.

The owner's linked conversation remains `Dự án StockRadar · Liên thông ChatGPT`, using reviewed handoff `PROJECT_CHAT_V1_20260907`. It was not recreated, and no private transcript was published. Shared public methodology remains `AI_CORE_V2_20260907`.

## What changed

The browser previously used an unowned localStorage thread pointer and copied authenticated history into the same buffer used by Guest requests. Server ownership checks blocked direct cross-account reads, but client account transitions and delayed responses needed explicit isolation.

Saved thread pointers are now scoped to the account; the legacy unowned pointer is ignored. Logout/account changes clear displayed history and the temporary buffer immediately. Late history, thread-list, model-answer, new-thread and resume responses are checked against the current account/session generation. Superseded history responses cannot replace a newer selection.

Authenticated history is restored from the server and never put in the Guest request buffer. Only implicit startup restoration can recover a missing pointer once through owned server history. An explicit failed sidebar selection does not silently select another conversation. Token refresh for the same account does not reload history over the current conversation.

`Tiếp tục từ dự án` resumes the server-linked conversation through read/history operations, without inference or question-quota consumption. The new status `Hội thoại dự án đã mở` refers to the opened conversation, not a successful model reply. Imported summaries are labelled `Bản tóm tắt chuyển từ dự án · không phải tin nhắn nguyên văn`.

## Verification evidence

Feature run `34073599794` passed syntax checks, the 106-test Node handler/client suite (including 15 new continuity cases), 37 reviewed/public/private loader tests, and both existing Python regression suites. The first feature attempt detected a whitespace-sensitive old source assertion; that assertion was changed to ignore formatting and additionally require ownership-checked selection. No behavioral or security test was removed.

The 15 new cases execute the real browser source in an isolated VM. They cover account-scoped storage, logout cleanup, summary labelling, Guest isolation, delayed responses, reauthentication as the same user, out-of-order history, pointer recovery and token refresh. These are synthetic account tests, not a live login to the owner's account.

The successful Pages pipeline also ran the existing regression, auth/product, Node and multi-viewport browser checks before publishing. A connected HTTP fetch of the deployed `assets/ai-center.js` (production response 48) returned HTTP 200 and confirmed all three new/current runtime features: the `Hội thoại dự án đã mở` status, `Tiếp tục từ dự án` control and `accountEpoch` session guard. The published asset is transformed/minified: raw source comments and whitespace-specific expressions are not deployment-verification criteria. Response 47 had still shown the old asset while deployment was in progress; it is superseded by response 48.

A connected database read rechecked the exact owned linked thread. At that checkpoint it contained only its original reviewed handoff note and no new website exchange. A private read cursor was recorded for that linked thread. No additional user messages were fabricated, no old messages overwritten, and no handoff/knowledge version was needlessly bumped.

## Remaining blocker and limits

A new production provider check, HTTP response 46, again returned `READY_FALLBACK`, `MODEL_CREDIT_BLOCKED` and `OPENAI_429_CREDIT_BALANCE_EXHAUSTED`. It returned no private bridge field. This verifies the configured provider route's block, not the owner's general billing state. No API credit was bought, no payment settings changed and no replacement key created.

That provider probe was a longer Vietnamese lookup sentence and was routed as `compare`, not `ticker`. Broader natural-language ticker recognition remains a separate issue; this client-continuity release does not claim to resolve all ticker routing. Previous short lookup `tra cứu FPT` had been verified independently. No stock recommendation is derived from this probe.

No API key, provider billing, quota, entitlement, payment approval, email gate, data gate or market-analysis rule was changed. Private reviewed handoff remains owner- and thread-scoped.

This is explicit reviewed project-to-website handoff plus authorized, on-request website-to-project history reads. It is not automatic message-by-message synchronization of all ChatGPT Project conversations. A successful live authenticated multi-turn model conversation remains unverified because the tested provider route is credit-blocked.
