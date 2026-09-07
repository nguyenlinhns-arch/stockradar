# Owned project record reads and knowledge-provider diagnostics

## Scope

A request only to inspect whether the current conversation is linked, which reviewed version is present, or the stored reviewed summary should read the existing owned record, not require a successful paid model inference. This change adds a narrowly matched read path to authenticated chat. Mixed stock-analysis, market, account-upgrade, email and payment requests remain on their ordinary routes. Technical burst limits remain enforced; pure record reads do not consume the daily AI question bucket. No new unauthenticated endpoint or privileged role is introduced.

A record-status response contains version and review time but not the private summary. Only an explicit summary request in the exact linked, authenticated owned thread includes the stored summary. The text is clearly labelled as a reviewed record, not a verbatim message or model-generated answer. Client-supplied context/owner ids are ignored. Loaded context and successful model application remain distinct. This is not automatic raw-message synchronization with ChatGPT Projects.

Knowledge-only inference now distinguishes a missing API key, provider authentication/access errors, provider rate limiting, provider credit/quota exhaustion, transport failure and incomplete/invalid replies. Only bounded error classes are returned; raw provider bodies, messages and secrets are never reflected. The existing provider, key, request settings and account entitlements are unchanged. Persistence is reported only after the existing save operation succeeds, and sanitized failure provenance is retained in message metadata.

## Verification

The pure helpers cover status/summary intent, mixed-request rejection, thread scoping and safe provider-error classification. Real chat-handler tests cover authenticated record reads without model configuration, private isolation, ignored forged content, technical throttling, truthful provider status, saved provenance and persistence metadata. The feature workflow runs these and all existing Node/Python and bridge tests before committing endpoint changes.

Source-preparation checkpoint: helper tests passed locally. Feature CI and deployment results must be recorded after observation. No claim of successful production authenticated model generation is made. The last earlier provider observation was credit-blocked; the subsequent live Guest probe hit the website quota before inference, so it was not a new provider-status check.

## Rollback

Only `stock-ai-chat` and a new pure helper change runtime behavior. Rollback can redeploy the previously pinned chat source; the private database schema, handoff content, public methodology, frontend assets, payment approval and email delivery are not changed by this release.
