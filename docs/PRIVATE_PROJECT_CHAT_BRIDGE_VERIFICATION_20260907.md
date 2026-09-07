# Private project conversation bridge — verification 2026-09-07

## Completed

The owner-requested private handoff has been provisioned in the existing server-only memory table and linked to a newly created owned conversation named `Dự án StockRadar · Liên thông ChatGPT`. Its version is `PROJECT_CHAT_V1_20260907`; exactly one explicitly labelled reviewed-summary note was inserted. The prior website conversation and its original messages were preserved. Real account identifiers and the private summary are intentionally omitted from this public audit.

The handoff was prepared after reading the owner's existing website conversation through the connected database. This provides an actual on-request website-to-project read, not an assertion that unseen or unrelated project chats were imported. The private summary carries the selected project decisions and the current continuation intent. It is distinct from the shared public methodology record `AI_CORE_V2_20260907`, which was not modified by this change.

## Runtime deployment

All three backend deployments are ACTIVE and pinned to verified source commit `2355479c13d54fd6873b37213f10444f61c733b3`:

| Function | Deployment version |
| --- | --- |
| stock-ai-chat | 4 |
| stock-ai | 29 |
| stock-ai-guest | 25 |

The guest deployment contains only the shared ticker-parser correction; it has no private project-context loader. Authenticated chat and research bind the handoff to the verified user id and the exact linked thread. Unrelated chats do not inherit it. Source code preserves existing custom authentication, market/data gates, paid entitlements and question quotas.

## Verification results

Feature workflow `34072433173` completed successfully. It applied the exact-source patch, ran the 22 isolated handoff tests, all Node handler/regression tests (including new synthetic owner/non-owner chat cases), both existing Python suites, frontend syntax checking and whitespace verification. It committed the modified endpoint/client source only after success.

Live smoke responses `40–43` were read from the production database HTTP response table:

| Check | Observed result |
| --- | --- |
| Guest question `tra cứu FPT` | HTTP 200; scope `ticker`; ticker `FPT`; shared knowledge `AI_CORE_V2_20260907`; no private bridge field returned |
| Model generation for that guest question | `READY_FALLBACK`, `MODEL_CREDIT_BLOCKED`, reason `OPENAI_429_CREDIT_BALANCE_EXHAUSTED` |
| Private `resume_project` operation without authentication | HTTP 401, `UNAUTHORIZED` |
| Private resume from an unapproved origin | HTTP 403, `FORBIDDEN_ORIGIN` |
| Anonymous direct Data API read of the memory table | HTTP 401, PostgreSQL permission code `42501` |

The private memory table was inspected: RLS enabled, no anon/authenticated table grants and no policies granting those roles access. Provisioning did not alter grants, RLS, paid accounts, payments, recipient lists or email delivery. The bridge points to an ACTIVE thread owned by the same verified account; exactly one provenance note exists for this version.

## Frontend checkpoint

The AI workspace source now has a `Tiếp tục từ dự án` control, displayed only when the server reports a bridge for the signed-in account. It resumes the server-selected owned thread without an inference request or question-quota charge. History hydration rechecks the active account before showing fetched history.

At this audit checkpoint, Pages run `34072504216` had passed backend regressions, static build, authentication/product checks and Node tests; multi-viewport browser QA was still in progress. A final Pages deployment is not claimed at this checkpoint. Backend deployment and private database provisioning above are complete independently of the Pages build.

## Remaining limits

This is an explicit reviewed handoff plus on-request reading of the owned website thread. There is no native automatic message-by-message synchronization of ChatGPT Project history. New project decisions require another reviewed handoff update. Website messages remain in the private linked thread and can be retrieved through the authorized connected database when the owner requests continuation here.

A live authenticated model conversation was not tested using the owner's browser session; synthetic authentication tests are not a substitute for that check. The currently tested provider route still reports depleted API credit. Persistence and restoration of context do not resolve that separate provider issue or establish that the model has successfully applied the handoff in production.
