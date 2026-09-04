# StockRadar authentication deployment

StockRadar uses GitHub Pages for the public site and Supabase Auth for identity. Passwords and OTPs are handled by Supabase; the static site never stores plaintext credentials.

Current Supabase project: `StockRadar` (`xamviatbxufjlpiwhebb`, Singapore).

Known GitHub Pages origin: `https://nguyenlinhns-arch.github.io/stockradar/`. The intended canonical product domain is `https://stockradar.vn/`; verify the active Pages custom-domain/DNS state before changing Auth URLs.

## Required Supabase Auth configuration

In **Authentication → URL Configuration**, the Site URL and redirects must match the host actually serving authentication flows.

For the GitHub Pages origin, exact redirects include:

- `https://nguyenlinhns-arch.github.io/stockradar/tai-khoan/`
- `https://nguyenlinhns-arch.github.io/stockradar/dat-lai-mat-khau/`

When `https://stockradar.vn/` is verified as the live canonical host, use that Site URL and add the equivalent `/tai-khoan/` and `/dat-lai-mat-khau/` redirects before switching auth traffic. Do not infer DNS readiness from repository state alone.

Keep email confirmations enabled.

## Versioned legal and email consent

Current versions are intentionally separate:

- Terms of Use: `2026-09-03`
- Privacy Policy: `2026-09-04`
- Product-email consent document: `2026-09-04`

Signup metadata records the terms and privacy versions separately. Public email-interest forms submit the current product-email consent version. `private.email_delivery_gate.current_consent_version` is `2026-09-04`; preferences without current granted consent are disabled fail-closed.

A policy bump must never silently reinterpret an older consent as consent to the new version. When changing the privacy/email consent version, update the public copy/client metadata and database current version together, then test that the new version is accepted and the old version is rejected.

## Email delivery launch gate

Production currently sets:

- `STOCKRADAR_AUTH_EMAIL_READY="0"`

This is intentional. While custom SMTP is not verified end to end, public signup, signup-OTP resend, login OTP recovery, and forgot-password sending fail closed in the browser. Normal sign-in for an existing verified account remains available.

After custom SMTP, sender domain, Auth URLs, OTP template, recovery template, and a real mailbox test all pass, change the production flag to:

- `STOCKRADAR_AUTH_EMAIL_READY="1"`

Do not flip this flag merely because SMTP credentials were entered; first complete an actual signup → email delivery → OTP verify → login → recovery test.

## Email templates

StockRadar uses a 6-digit email OTP for signup verification. In **Authentication → Email Templates → Confirm signup**, use the versioned repository template:

- `supabase/email-templates/confirm-signup.html`

The template must contain `{{ .Token }}`. If the confirmation template only contains `{{ .ConfirmationURL }}`, Supabase sends a link instead of the six-digit OTP expected by the signup UI.

For password recovery use:

- `supabase/email-templates/recovery.html`

The default hosted sender is testing-only and is not the public product delivery channel. Before opening arbitrary-user email flows, connect a custom SMTP provider and verify its sending domain.

## Production build configuration

The Pages workflow publishes only the Supabase project URL and a browser-safe `sb_publishable_...` key. Never expose a secret/service-role/SMTP key.

Production release sequence:

1. `python -m engine.cli build-public`
2. `python -m unittest discover -s engine/tests -v`
3. `python scripts/build_pages.py --output .pages-site` with auth enabled and public Supabase config.
4. Apply production-facing UX/buyer-readiness guards.
5. Run production auth, public-surface and buyer-ready verifiers.
6. Install pinned Playwright/Chromium and run multi-viewport visual QA against the built artifact.
7. Only after all checks pass may GitHub Pages upload and deploy.

The visual gate covers 15 actually published routes at desktop, tablet and mobile sizes (45 route/viewport checks). It fails on non-200 responses, missing main/H1/title, horizontal overflow, relevant console/page errors, broken mobile navigation and undersized primary controls.

The workflow uses `cancel-in-progress: true`, so a newer `main` commit cancels stale Pages runs and becomes the only release candidate.

## Implemented flows

- Signup: email + password + separately versioned terms/privacy consent.
- Signup confirmation: six-digit email OTP using `verifyOtp`.
- Resend signup OTP with a persistent 60-second UI cooldown plus Supabase server-side rate limiting.
- Resume verification from the login page for users who registered but have not confirmed their email.
- Fail-closed production email gate until custom SMTP is ready.
- Sign in with email + password.
- Persistent managed session and automatic token refresh.
- Sign out.
- Forgot-password email and reset page.
- Change password while signed in only after supplying the current password; recovery-token password reset remains separate.
- User profile in `public.profiles`: default tier `FREE`; status moves from `PENDING` to `ACTIVE` after email verification.
- RLS restricts profile/watchlist/preference rows to the signed-in user and does not let the browser edit entitlement fields.
- Versioned legal/product-email consent receipts created by server-side flows.
- Public Terms and Privacy pages; Privacy Policy current version is 2026-09-04.
- Self-service account deletion requires current-password reauthentication, explicit `XOA` confirmation, a verified user JWT and a Supabase `session_id` created within the previous five minutes.
- `delete-account` Edge Function is source-controlled, JWT-protected, origin-restricted and checks the recent session through a service-role-only RPC before calling `auth.admin.deleteUser`.
- Payment and subscription audit rows do not block deletion: their user FKs use `ON DELETE SET NULL`, preserving reconciliation history while removing the direct deleted-account link.
- Production rollback tests verify both the billing-history deletion behavior and the recent-session gate without leaving test data.
- Authenticated stock-report requests use private operational observability that does not retain JWT/IP/email/user-agent/report payload.
- Global login/register or account/logout controls on deployed HTML pages.

## Security boundaries

- Passwords and OTPs are never sent to StockRadar market-data/analytics endpoints.
- Pending signup email is stored only in session storage for UX continuity; password and OTP are not persisted there.
- Public Pages code may contain only the Supabase project URL and publishable key.
- Secret/service-role/SMTP credentials remain server-side only.
- Paid entitlement must come from trusted backend/billing state, never client-editable metadata.
- Browser roles cannot invoke recent-session deletion verification or private stock API audit RPCs directly.
- Never collect broker passwords, trading OTPs, broker API secrets, order credentials, NAV, bank OTPs, or portfolio-control credentials through StockRadar authentication.

## Release checks after Auth/privacy changes

- GitHub Actions regression suite: PASS.
- Production auth artifact verifier: PASS.
- Production public/buyer-ready verifiers: PASS.
- Multi-viewport Chromium visual QA: PASS.
- Supabase Security Advisor: no new application WARN/ERROR.
- Supabase Performance Advisor: no new actionable WARN/ERROR.
- Verify effective browser grants remain least-privilege after schema changes.
- For deletion changes, rerun billing-history SET NULL and recent-session rollback tests.
- For privacy/consent changes, verify current consent is accepted and the prior version is rejected using rollback-safe tests.
- Test one real signup mailbox end to end after any email-template, SMTP, Site URL, redirect, or canonical-domain change.
