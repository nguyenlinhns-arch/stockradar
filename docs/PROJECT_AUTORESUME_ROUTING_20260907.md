# Project auto-resume and Vietnamese routing — released 2026-09-07

## Outcome

The owner-requested automatic restoration of the linked private project conversation is implemented, enabled for the verified owner account, and published. Final frontend source is commit `3a9f09bbaf151ec23969885a68413cf1302bb99a`. Pages run `34074961227` completed successfully for both build and deploy, including multi-viewport browser QA.

A direct production fetch of `assets/ai-center.js`, recorded as HTTP response 52, returned HTTP 200 and confirmed all four deployed features: `project-auto:` versioned restoration marker, `auto_resume` server opt-in check, `restoreSequence` startup race guard, and the `Hội thoại dự án đã mở` status. This verifies the published asset, not an interactive login to the owner's browser.

## Automatic restoration

On authenticated initial page restoration, the client checks the server-owned private bridge. With `auto_resume: true`, it opens the linked conversation once per reviewed handoff version and account/browser. After that first successful restoration, manually selecting a different conversation is respected. Accounts without opt-in retain ordinary history restoration.

The owner bridge was updated transactionally under an advisory lock, with checks for verified account identity, expected handoff source/version, and ownership of an ACTIVE linked thread. Only `auto_resume`, its activation timestamp and reason were added. The existing conversation `Dự án StockRadar · Liên thông ChatGPT`, handoff version `PROJECT_CHAT_V1_20260907`, 3,249-character summary and original single reviewed note were preserved. No extra conversation or fabricated user exchange was inserted. Real account identifiers and private summary contents are deliberately omitted from this public audit.

Restoration calls only metadata/history operations; it does not invoke the model or consume an AI question quota. The composer remains guarded throughout initial restoration, including the metadata request, so a question cannot be submitted into the wrong thread during startup. Responses from an older account/session cannot unlock or replace the new account's restoration.

## Vietnamese intent corrections

One canonical lexical recognizer is embedded in research parsing, authenticated chat and browser entry points. It preserves Unicode/accent boundaries, masks lookup phrases, URLs and email addresses, and distinguishes ordinary three-letter words from explicit stock mentions.

Regression tests now cover the exact previously failing sentence `Tra cứu FPT; chỉ dùng dữ liệu có nguồn và ghi rõ ngày dữ liệu.` as a single FPT request. An initial regression run also caught a real issue with the explicitly named comparison `So sánh DAT và MBB`; the recognizer was corrected, and the existing test was preserved rather than weakened.

Explicit message tickers supersede stale client selections. Discussing a sector for one named ticker no longer necessarily triggers a full-market scan. A follow-up such as `Có Pocket Pivot chưa?` retains the current ticker, explanatory methodology questions remain knowledge questions, and explicit investment horizons such as `3–6 tháng thì sao?` are inferred server-side. Project-context questions are routed to the knowledge conversation without inventing a stock symbol.

This remains lexical intent recognition, not an authoritative market listing or a guarantee of perfect interpretation. Existing HOSE, freshness, data-rights and action checks still determine whether research or a trading signal may be returned.

## Backend deployment

The three production functions were deployed from verified source commit `598f94b8c51b0f3491b515899f14b4563643f659`:

| Function | ACTIVE deployment version |
| --- | --- |
| stock-ai-chat | 5 |
| stock-ai | 30 |
| stock-ai-guest | 26 |

The later final source commit adds only frontend startup-lock code, tests and workflow/scripts; backend behavior is unchanged from that deployed commit. Existing custom authentication settings were preserved. The guest endpoint has no private project-context loader.

## Verification

Feature run `34074641047` passed after the ambiguous-symbol correction. Feature run `34074904311` passed after the additional startup-lock tests. The latter workflow ran the complete Node handler/client suite, the 37 shared/private knowledge-loader tests, both existing Python regression suites, JavaScript syntax checks and whitespace checks before committing generated source. The final Pages workflow subsequently passed regression, auth/product, checkout and browser QA checks before publication.

The new cases include exact long-question routing, ticker changes, comparison and sector intent, follow-up ticker/horizon continuity, opt-in restoration once per version, preservation of manual thread selection, metadata failure fallback, cross-account late responses and startup submission races. These are synthetic tests executing real handler/client code; they are not a live authenticated model conversation.

Private store verification after activation confirmed RLS enabled, zero direct anon/authenticated table grants, matching owner/thread identity, and the original summary/note count unchanged. Live requests without authentication or from an unapproved origin returned 401 and 403 respectively and disclosed no private bridge data.

## Live inference status — distinguish the two limits

| Evidence | Actual result |
| --- | --- |
| New post-deployment long-query probe, HTTP response 49 | HTTP 429, `RATE_LIMITED`, at the website Guest quota. No model or ticker-routing result was returned. |
| Unauthenticated project metadata probe, response 50 | HTTP 401, `UNAUTHORIZED`, no private metadata. |
| Unapproved-origin private resume probe, response 51 | HTTP 403, `FORBIDDEN_ORIGIN`, no private metadata. |
| Earlier provider-level probe, response 46 | HTTP 200 deterministic fallback, `MODEL_CREDIT_BLOCKED`, reason `OPENAI_429_CREDIT_BALANCE_EXHAUSTED`. |

The latest live query did not reach inference, so it cannot be used to claim a fresh provider billing diagnosis or a successful live corrected-ticker answer. The provider-credit error is an earlier observation, while the latest limitation is the Guest usage quota. Quotas were not reset or bypassed, account tokens were not fabricated, no replacement API key was created and no credit was purchased. Successful live authenticated multi-turn model generation remains unverified.

## Operating boundary

This release provides automatic opening of the existing reviewed project handoff on the website, plus authorized on-request reading of owned website history. It is not native, continuous, raw-message synchronization of every ChatGPT Project conversation. New project decisions still require an explicit reviewed handoff update.

Private handoff text remains owner- and thread-scoped. No portfolio, recipient list, private transcript, credential or real account identifier was published in this change. Shared public methodology stays at `AI_CORE_V2_20260907`. Entitlements, payment approval, email delivery, market data and action gates were not changed. Saving or opening context does not itself establish that an AI model successfully used it.
