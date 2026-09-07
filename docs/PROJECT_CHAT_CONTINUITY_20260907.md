# Project chat continuity — 2026-09-07

## Outcome at this checkpoint

Account/session-safe conversation continuity is implemented in main at source commit `12603ba673a57b3aecffdae0cf517eb83fe710ed`. Feature verification run `34073599794` completed successfully before merge. This is a browser continuity repair; backend AI functions, provider configuration, account rights and market-analysis logic were not changed.

The previously deployed private bridge is already live: Pages run `34072504216` completed successfully, including multi-viewport browser QA and deployment. Production HTTP response 45 returned status 200 for `assets/ai-center.js`, with both `Tiếp tục từ dự án` and `resume_project` present. The owner's existing linked conversation remains `Dự án StockRadar · Liên thông ChatGPT`, using reviewed handoff `PROJECT_CHAT_V1_20260907`. It was not recreated, and no private transcript was published.

## Repair

The browser previously used an unowned localStorage thread pointer and copied authenticated history into the same buffer used by Guest requests. Server ownership checks blocked direct cross-account reads, but client account transitions and delayed responses still needed explicit isolation.

The repair scopes saved thread pointers to the account and ignores the legacy unowned pointer. Logout/account changes clear displayed history and the temporary buffer immediately. Late history, thread-list, model-answer, new-thread and resume responses are checked against the current account/session generation. Superseded history requests cannot replace a newer selection.

Authenticated history is restored from the server and is never put in the Guest request buffer. Only an implicit startup restoration can recover a missing pointer once through owned server history. An explicit failed sidebar selection does not silently select another conversation. Token refresh for the same account does not reload history over the current conversation.

The existing project-resume control remains a read/history operation, not an inference request. The new status `Hội thoại dự án đã mở` refers to the opened conversation, not a successful model reply. Imported summaries are labelled `Bản tóm tắt chuyển từ dự án · không phải tin nhắn nguyên văn`.

## Verification evidence

Feature run `34073599794` passed syntax checks, the 106-test Node handler/client suite (including 15 new continuity cases), 37 reviewed/public/private loader tests, and both existing Python regression suites. The first feature attempt detected a whitespace-sensitive old source assertion; that assertion was changed to ignore formatting and additionally require ownership-checked selection. No behavioral or security test was removed.

The 15 new cases execute the real browser source in an isolated VM. They cover account-scoped storage, logout cleanup, summary labelling, Guest isolation, delayed responses, reauthentication as the same user, out-of-order history, pointer recovery and token refresh. These are synthetic account tests, not a live login to the owner's account.

A connected database read rechecked the exact owned linked thread. At this checkpoint it contained only its original reviewed handoff note and no new website exchange. A private read cursor was recorded for that linked thread. No additional user messages were fabricated, no old messages overwritten, and no handoff/knowledge version was needlessly bumped.

A new production provider check, HTTP response 46, again returned `READY_FALLBACK`, `MODEL_CREDIT_BLOCKED` and `OPENAI_429_CREDIT_BALANCE_EXHAUSTED`. It returned no private bridge field. This verifies the current configured provider route's block, not the owner's general billing state. It does not establish successful live model generation.

## Deployment checkpoint

Pages run `34073650993` is publishing the continuity source. At this document checkpoint its regression, auth/product and Node checks had passed, and multi-viewport browser QA was in progress. The final result and live new-asset verification must be appended after observation. The older project-resume control is already published as verified above.

## Boundaries

No API key, provider billing, quota, entitlement, payment approval, email gate, data gate or market-analysis rule was changed. The shared public knowledge remains `AI_CORE_V2_20260907`; the private reviewed handoff remains owner- and thread-scoped.

This is explicit reviewed project-to-website handoff plus authorized, on-request website-to-project history reads. It is not automatic message-by-message synchronization of all ChatGPT Project conversations. A successful live authenticated multi-turn model conversation remains unverified because the tested provider route is credit-blocked.
