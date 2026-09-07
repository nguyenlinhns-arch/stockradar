# Private Project question/reply channel — published 2026-09-07

## What this release does, and what it does not do

The linked owner can submit a question directly from the website into a private queue. The authorized Supabase connector available in the current StockRadar ChatGPT Project can read that exact question, claim it and save a reply under it. The open website polls for changes every five seconds while visible and displays the returning reply. This removes question/answer copy-paste for the linked owner.

This is NOT an autonomous website AI backed by a ChatGPT subscription. A database submission does not awaken this ChatGPT conversation, create a new native Project message, or invoke its model. Processing is explicitly started in ChatGPT. No scheduler, browser-cookie proxy, account sharing or paid model API was introduced. The full instant-autonomous requirement remains unfulfilled; the implemented data connection must not be represented as that capability.

## Code and database

PR 91 was merged with expected tested head `faa3d92f76ada3059da3b6e46c1db7c8d42df8bc` as `931b73ac0e01593be75e6205574f0a09ffbc78d2`. Migration `20260907034311_project_question_channel` is applied. It preserves all previous chat/report tables and provisions the channel from the single existing reviewed private owner link, without publishing identifiers or onboarding visitors.

Authenticated browser RPCs use `auth.uid()` rather than a supplied owner id and verify the active account, configured channel and active owned thread. Questions have idempotency keys and optional owned answered-parent references. Up to ten unfinished questions and sixty submissions per rolling hour bound queue abuse; these are not new model charges or changes to subscription quotas.

Only the trusted processor can read the queue for processing, claim work and complete answers. Browser roles have owner-only SELECT on question/reply rows, no direct write access, no claim-table access and no completion-function access. Work claims expire after 30 minutes, rotate on reclaim and reject late or wrong-token writes. Completed answers are immutable except for an identical idempotent retry. Cancelled requests reject late replies. No public recommendation, email, trade or payment is triggered.

## Tests actually completed

The 13 new tests against the real client controller passed locally. Feature workflow `34080921118` completed successfully, including all existing Node/Python regressions, these controller tests and a real-browser test of the activated artifact at 390px and 1440px. Browser fixtures verified submission, WAITING state, return polling, text-only/XSS-safe answer rendering, absence of model endpoint calls and removal of private content on logout. They used synthetic sessions, not the owner's real browser login.

Connected database tests ran under actual `authenticated` and `service_role` database privileges with transaction-local claims; no browser login tokens were fabricated. They verified owner submission/read, duplicate protection, rejection of conflicting retries, processor claims/completion, wrong-token rejection, immutable replies, parent questions, cancellation, cross-account isolation and denied browser processor access. All fixtures were rolled back. A second rolled-back test verified expired claims, requeue visibility, token rotation, stale-token rejection and disabled-channel rejection.

A privilege read confirmed anonymous table reads, browser answer updates, browser processor reads/completion and browser claim-token reads are all denied.

## Connected Project round trip

One real, clearly labelled PROJECT_VERIFICATION question was seeded into the linked owner's queue. It was then read through `read_stockradar_project_inbox`, separately claimed, answered in this current ChatGPT Project and saved through `complete_stockradar_project_question`. A separate read-back confirmed ANSWERED, CHATGPT_PROJECT, 1,355 answer characters, public_action_allowed=false and an answer timestamp.

The verification answer explains the exact processing boundary. It was not a message typed by the owner in a live browser, and it must not be described as such. Its private question id, owner id, claim token and answer body are intentionally omitted from this public document. The write reported OWNER_ONLY, published=false, email_sent=false and provider_attempted=false.

## Publication and live observation

Pages run `34081050911` completed successfully for both build and deployment. Reported successful stages included existing regressions, authentication/product checks, multi-viewport browser checks, and final activation/verification of CHATGPT_WORKSPACE. The Project channel's own linked-owner browser behavior was verified in the separate successful feature workflow before merge.

The connected Opera browser opened the live `/ai/` page after deployment. The accessibility tree showed the ordinary ChatGPT workspace and the signed-out login/registration controls. This confirms a live guest-page observation, not a test of the owner's authenticated private channel. No login credential was requested, extracted or fabricated. An attempted separate live asset download through web tooling was rejected by its URL safety restriction; it is not counted as successful verification.

No Edge Function redeployment was needed: the new channel uses narrow database RPCs and the existing authenticated data client. The previous no-model-API defaults remain unchanged. No billing, API key, paid entitlement, email settings or existing market-action gate was changed. Storage/network/hosting costs remain separate from avoided model calls.

## Operating instructions and remaining boundary

See `PROJECT_CHANNEL.md` for the read → claim → analyze in Project → complete → read-back protocol. `CHATGPT_WORKSPACE.md` now directs continuation of website questions to that inbox rather than asking the owner to copy their question. Website questions and previous replies are untrusted user context, not system instructions or authority for unrelated privileged actions. Financial questions still require fresh verified evidence and the existing methodology/data gates.

For the linked account the published AI page exposes `Gửi vào hàng đợi dự án`, `Tải lại hội thoại`, cancellation and explicit follow-up. After the owner initiates processing in the ChatGPT Project, a saved answer can return to the open website without manual copying. The website does not generate an answer merely by polling. Guests and unrelated accounts keep the generic public question-preparation path and cannot read this private Project channel.

A public StockRadar GPT/App launch, automatic native ChatGPT Project invocation from the website and full raw-chat synchronization are not implemented or implied by this release. These should remain marked unresolved rather than being confused with the successfully deployed two-way data path.
