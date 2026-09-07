# Owned project record reads — deployed 2026-09-07

## Outcome

The authenticated chat backend has been updated and deployed as `stock-ai-chat` version 6, status ACTIVE, pinned to verified source commit `dd92154beeed51d294774ada5d99bcc22dd22ced`. Feature workflow `34075884891` completed successfully before the source was fast-forwarded into main and the backend deployed. The frontend was unchanged; an unnecessary Pages rebuild was not triggered.

The owner's existing private conversation `Dự án StockRadar · Liên thông ChatGPT` now carries reviewed handoff `PROJECT_CHAT_V2_20260907`. This is an actual update to the private project context, not only a code change. The original handoff and prior messages were preserved. Exactly one labelled V2 update note was added, and the existing summary was extended to 4,838 characters, within the loader's 6,000-character limit. Automatic restoration remains enabled. Real account identifiers and private summary contents are not included in this public document.

## Reading stored project context without model inference

A narrowly matched request only to inspect whether the current conversation is linked, which reviewed version is present, or to view the stored reviewed summary now reads the server record. It does not depend on a successful model call. Examples covered by handler tests include `Đã liên thông với dự án chưa?` and `Xem ngữ cảnh dự án đã chuyển`.

The caller is authenticated, account access is checked, and the exact owned thread is resolved before this branch runs. A status answer includes the reviewed version/time but not the summary. Only an explicit summary request in the exact linked thread includes its private summary. Another account or unrelated thread receives no private summary. Client-supplied context and owner ids have no authority.

Record reads are labelled `PROJECT_HANDOFF_RECORD`, `MODEL_NOT_CALLED`, `provider_attempted: false`, and `quota_consumed: false`. These are stored-record responses, not new model-generated analysis. The existing technical burst limiter remains enforced before the response is stored. Ordinary market-analysis questions retain their existing data/action and AI quota paths; mixed stock-analysis, market, upgrade, email and payment requests are not converted into free record reads.

## Knowledge-provider diagnostics and persistence

The knowledge-only inference path now distinguishes missing API configuration, provider authentication/access errors, provider speed limits, provider credit/quota exhaustion, transport failure, and incomplete/invalid replies. Missing configuration is no longer labelled as exhausted credit. An API 429 with credit/quota evidence is distinguished from ordinary provider rate limiting and from the website's own question limit.

Only bounded error classes are returned. Raw provider error bodies, messages and secrets are not reflected. Provider/model configuration and inference request parameters are unchanged. Failed generation never claims that reviewed knowledge was successfully applied. The response reports `conversation_persisted: true` only after the existing save operation succeeds, and sanitized failure provenance is retained in message metadata for later inspection.

## Verification actually performed

Workflow `34075884891` passed the new pure-helper tests, real chat-handler tests, all current Node/Python regressions, and shared/private knowledge-loader suites. Positive record-read cases used the real handler with synthetic authenticated accounts and database fixtures; they did not use the owner's real browser session. Cases included no model key, ignored forged context, unrelated account isolation, burst throttling, specific credit failures, missing-key classification, provenance storage and truthful persistence.

After production deployment, live HTTP responses 53 and 54 confirmed that an unauthenticated record question is rejected with HTTP 401 (`UNAUTHORIZED`), and an unapproved-origin request is rejected with HTTP 403 (`FORBIDDEN_ORIGIN`). Neither returned an answer or private bridge data. These verify access rejection, not a successful authenticated live model conversation.

The private V2 handoff update ran under an advisory lock and checked the verified owner, expected prior source/version, active linked thread and size limit before writing. A post-write query confirmed matching owner/thread identity, automatic restoration still enabled, exactly one V2 note, RLS enabled on the memory table and zero direct anon/authenticated table grants. No account entitlements, payment approvals or email-recipient settings were changed.

## Remaining boundary

No fresh live model inference was attempted during this deployment, and no user token was fabricated or obtained from a private session. The earlier provider-level observation was credit-blocked; the subsequent Guest probe was stopped by the website quota before inference. Those are different observations, not proof of the current provider billing state. No quota was reset, no replacement API key created, and no API credit purchased.

A successful production authenticated multi-turn model conversation is still unverified. Direct record reads are useful while inference is unavailable, but are not a substitute for model-generated stock analysis.

The bridge remains an explicit reviewed project-to-website context transfer plus authorized on-request reading of website history. It does not automatically import raw messages from every ChatGPT Project conversation. The public methodology store remains separate from the private handoff; no private portfolio, recipient list or raw conversation was published.

## Rollback

Runtime behavior can be rolled back by redeploying the previous `stock-ai-chat` source. The private V2 note is a labelled record of completed project decisions and should not be deleted or rewritten as though the update never happened. No database schema migration was required.
