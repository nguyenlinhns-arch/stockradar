# StockRadar project knowledge bridge — 2026-09-07

## Outcome

The shared project-knowledge bridge is implemented and deployed to the three production AI endpoints. A live guest request loaded `AI_CORE_V2_20260907`. Live model generation is NOT verified as working: the configured provider route returned `OPENAI_429_CREDIT_BALANCE_EXHAUSTED`, and the response correctly remained a deterministic fallback with `knowledge_applied: false`.

This is a reviewed project-knowledge snapshot, not direct access to a ChatGPT Project and not automatic two-way synchronization of every chat message.

## Scope and implementation

The existing `stock-ai-chat` endpoint stores per-user threads and messages and already loaded project knowledge for methodology answers. The `stock-ai` and `stock-ai-guest` research paths previously used only their compiled static system core. The shared `stockradar-knowledge.ts` loader now supplies the active reviewed version to all three endpoints.

Knowledge is selected server-side from `public.stockradar_ai_knowledge_versions`. Client request bodies cannot supply or activate system knowledge. Only the existing reviewed source and the explicitly public reviewed source are accepted. Invalid, future, oversize or email/secret-bearing knowledge falls back to the existing static core. These checks are defense in depth, not a substitute for human privacy review.

The model receives the existing Data/Action/privacy core, reviewed project methodology, and an immutable reminder that prior conversation is context, not system instructions or live market evidence. Response metadata distinguishes which knowledge version was loaded from whether a successful model answer actually applied it. Completed but malformed model replies, incomplete replies and provider failures must not claim successful model generation.

Authenticated chat keeps its ownership checks and saves the downstream knowledge version actually used. Guest/Free/Paid quotas, account rights, payment approval, product-email gates and licensed-data gates are unchanged. No raw private project transcript, portfolio, administrator recipient list or credentials were copied into public project knowledge.

## Production record

Verified using the connected Supabase project on 2026-09-07:

| Endpoint | Active deployment version |
| --- | --- |
| `stock-ai` | 28 |
| `stock-ai-guest` | 24 |
| `stock-ai-chat` | 3 |

The deployments were pinned to repository source commit `eaff6cee04b360fda068fe6a69ce236bf39f2247`. Subsequent commits changed regression tests and this audit document, not deployed handler behavior. The existing custom-authentication deployment configuration was preserved.

The active knowledge record is `AI_CORE_V2_20260907`, source `PROJECT_STOCKRADAR_PUBLIC`. V1 was retained as a retired version. This activation does not refresh market prices or financial statements.

## Live checks

Evidence: server-side HTTP smoke responses 36–39, read from `net._http_response`. These checks did not impersonate an account, alter billing or expose secret credentials.

| Check | Observed result |
| --- | --- |
| Guest research request from the allowed website origin | HTTP 200; `knowledge_status: ACTIVE`; `knowledge_version: AI_CORE_V2_20260907`; `knowledge_sync_mode: REVIEWED_PROJECT_SNAPSHOT` |
| Provider/model result for that request | `READY_FALLBACK`; reason `OPENAI_429_CREDIT_BALANCE_EXHAUSTED`; `model_status: MODEL_CREDIT_BLOCKED`; `answer_engine: STOCKRADAR_CORE`; `knowledge_applied: false` |
| Chat history without authentication | HTTP 401, `UNAUTHORIZED` |
| Signed-in research endpoint without authentication | HTTP 401, `UNAUTHORIZED` |
| Guest request with an unapproved origin | HTTP 403, `FORBIDDEN_ORIGIN` |

The credit error is evidence about the provider route configured for this website, not an audit of every billing account belonging to its owner. No API credits were purchased, no payment settings were changed, and no replacement key was created.

## Regression verification

The shared loader's 15 behavior tests and four Python integration/structural tests passed during feature verification. Initial full regression runs exposed obsolete source-location assertions, missing dependency bindings in the handler mocks, and a mock success answer that did not satisfy the real four-layer/four-horizon response contract. Those tests were corrected without weakening production data, privacy, authentication or response-format checks.

Commit `89346a27beba6e8df8bd02788b51586141527b43` adds a contract-valid synthetic provider answer and explicit coverage for completed but malformed replies. Both research handlers are tested for successful reviewed-knowledge application, database-read fallback, ignored client knowledge overrides, quota denial before model calls, stale data, and account-scoped context.

GitHub Actions run `34071454307` reported `Run regression suite: success`. Static Pages build, production authentication verification, product contract verification and closed-checkout verification also passed. At this audit checkpoint browser QA and Pages deployment had not yet completed; their final result is not claimed here. The three backend deployments and live checks above were completed independently of that frontend pipeline.

## Remaining boundary and blocker

Future project decisions still require selection, privacy review and activation as a new knowledge version. New ChatGPT messages are not automatically read or published to the website, and website chats are not automatically imported into this ChatGPT conversation. Market evidence continues to come from fresh, verified StockRadar data.

To verify a complete live AI conversation, the website's configured API route must first have available credit/quota. Successful authenticated model generation and a multi-turn live browser conversation remain unverified. Fixing knowledge synchronization alone cannot resolve a provider billing block.
