# ChatGPT workspace / no duplicate model API — released 2026-09-07

## Delivered operating mode

The approved workflow is now deployed: analysis takes place in the existing ChatGPT Project, while StockRadar prepares questions, preserves earlier history and stores selected private reports. The website no longer needs a separate OpenAI inference call to regenerate a Project answer. This is a change of execution mode, not a claim that the old provider credit balance was repaired.

Verified implementation commit: `3e100ae736f0a6845fdea8f38abd6f25a63c43e7`. Later documentation/comment changes do not alter deployed behavior. Default execution is `CHATGPT_WORKSPACE`; enabling the legacy API path requires an explicit server-side `STOCKRADAR_INFERENCE_MODE=API`. Request bodies cannot enable that mode. No API key was created or changed, no quota reset and no credit purchased.

| Deployed function | ACTIVE version |
| --- | --- |
| stock-ai | 32 |
| stock-ai-guest | 28 |
| stock-ai-chat | 8 |

The three functions are pinned to the verified commit using simple import wrappers, preserving existing custom authentication. Initial wrappers that also set a runtime environment value returned HTTP 503 in smoke tests. They were replaced with the simple wrappers; subsequent smoke checks succeeded. The no-API default is implemented in shared source, not by runtime environment mutation.

## Website and public-user boundary

The published AI page now offers local question preparation, a copy action and `Mở ChatGPT`. It explicitly states that this opens ordinary ChatGPT, not a published dedicated StockRadar GPT or App. No private Project link, internal GPT, account cookie, subscription sharing or transcript proxy is exposed. The plain destination URL contains no prompt, account or history parameters. The question packet does not claim to include current market data.

Visitors use their own ChatGPT account and its limits. Their answers are not scraped or automatically imported into StockRadar. For the project owner, the already connected database tools in this ChatGPT Project provide data reads and selected-report writes. A separately published public StockRadar GPT/App remains outside this delivered first phase.

Delivered routes: `/ai/` and `/bao-cao-chatgpt/`. Legacy inference widget scripts are removed from the final Pages artifact; previous source remains only for compatibility tests and an explicit rollback. Selected reports are read from the authenticated owner's database rows, never embedded in public static HTML. Existing account rights, payment approval rules and email infrastructure were preserved.

## Genuine Project-to-StockRadar save

A real operational note titled `StockRadar × Project ChatGPT: quy trình phân tích và lưu báo cáo` was written in this Project and saved through `public.save_stockradar_workspace_report`. A separate read-back confirmed the owner-scoped row, 2,440 content characters, three evidence records and a stable content hash. Its source is `IMPLEMENTATION_NOTE`, status `DRAFT`, visibility `OWNER_ONLY`. It is not stock research, a current-price assertion or a trade signal.

The save did not invoke a second model, publish content, send email or create a trading action. The public repository intentionally omits the owner identifier, private report id and report body. An owner-scoped workflow preference records the new execution mode while preserving the existing V2 handoff and earlier chat messages.

For future selected analyses, the writer accepts title, body, stable idempotency key and optional ticker, horizon, evidence time and source array. It never converts a private report into an approved public recommendation. Publication/email would require a separate explicit action and the existing data/privacy checks.

## Database verification

Applied production migrations:

- `20260907025732_stockradar_chatgpt_workspace_reports`
- `20260907030602_workspace_verified_owner_lookup`

The reports table has RLS enabled and an authenticated owner-only SELECT policy. Anonymous SELECT is denied. Browser roles cannot insert, update, delete or execute the trusted save function. Report states are limited to DRAFT and ARCHIVED. The writer is SECURITY INVOKER. A narrowly scoped, non-exposed private SECURITY DEFINER helper returns only a verified-owner boolean to the trusted service role; it does not grant that role SELECT on auth.users.

Actual rolled-back database tests verified idempotent repeated saves, rejection of changed content under the same key, owner visibility, other-owner invisibility and a successful save under the real service_role privileges. This is a database policy test, not a fabricated browser login. Security-advisor output had existing unrelated findings; no global clean-security claim is made.

## Regression, browser and live deployment evidence

Feature workflow `34078766411` succeeded before merge. The preceding run had already passed all tests but could not push a changed workflow with the restricted Actions token; the workflow change was committed through the authorized repository connector, not by escalating that token. Coverage included 157 Node tests, 61 knowledge/context helper tests, 477 Python unittest tests and the pytest suite (479 tests plus 30 subtests).

Pages workflow `34078833870` completed successfully for build and deployment. It ran the existing compatibility checks, then activated the new final artifact and ran a dedicated real-browser workspace check on that delivered artifact. The new browser cases used 390, 768 and 1440-pixel viewports to exercise question preparation, a plain ChatGPT destination, absence of legacy widget scripts, no model-endpoint requests and no horizontal overflow. A synthetic authenticated report fixture tested text-safe rendering and immediate removal on logout. These fixtures are not evidence of an interactive login to the owner's actual browser.

Production HTTP smoke results from the connected database:

| Response | Observed result |
| --- | --- |
| 58: guest question handoff | HTTP 200, HANDOFF_READY, CHATGPT_WORKSPACE, MODEL_NOT_CALLED, provider_attempted=false, quota_consumed=false, generated_analysis=false, includes_private_history=false |
| 59: signed-in endpoint without authentication | HTTP 401, UNAUTHORIZED |
| 60: chat history without authentication | HTTP 401, UNAUTHORIZED |
| 57: anonymous direct report-table read | HTTP 401, PostgreSQL permission code 42501 |
| 61: published `/ai/` | HTTP 200; new workspace script loaded; no legacy ai-center script |
| 62: published private-report page shell | HTTP 200; new reader host/script; no private report content embedded |
| 63: published execution config | HTTP 200; CHATGPT_WORKSPACE present |
| 64: published workspace script | HTTP 200; local prepare action and new mode present; no api.openai.com literal |

The guest handoff succeeds without resetting its earlier exhausted daily inference quota because it performs no inference and consumes no AI-question quota. This is not a mechanism for bypassing model limits. No fresh paid model invocation was needed to complete this release.

## Remaining limits

This is a working first-phase Project/data/report workflow, not native raw-message synchronization of every ChatGPT Project conversation and not a public GPT/App launch. The generic website handoff requires the visitor to paste the prepared question in ChatGPT. The owner can remain in the current Project and request data reads and report saves through the connected tools.

ChatGPT usage remains subject to the user's plan, while hosting, storage, market-data and email costs remain separate. Only the retired website-chat model calls are avoided; no claim is made that every third-party service is free or that the owner's subscription supplies AI to all customers. An end-to-end private report display in the owner's live authenticated browser has not been personally exercised; storage, policy, deployed assets and synthetic browser behavior were verified separately.
