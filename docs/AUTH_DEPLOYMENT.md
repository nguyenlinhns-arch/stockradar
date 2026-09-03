# StockRadar authentication deployment

StockRadar uses GitHub Pages for the public site and Supabase Auth for identity. Passwords and OTPs are handled by Supabase; the static site never stores plaintext credentials.

Current Supabase project: `StockRadar` (`xamviatbxufjlpiwhebb`, Singapore).

Current temporary production URL: `https://nguyenlinhns-arch.github.io/stockradar/`.

## Required Supabase Auth configuration

In **Authentication → URL Configuration**:

- Site URL: `https://nguyenlinhns-arch.github.io/stockradar/` while GitHub Pages is the live host.
- Add exact redirects:
  - `https://nguyenlinhns-arch.github.io/stockradar/tai-khoan/`
  - `https://nguyenlinhns-arch.github.io/stockradar/dat-lai-mat-khau/`

When `https://stockradar.vn/` becomes the live canonical host, replace Site URL with that domain and add the equivalent `/tai-khoan/` and `/dat-lai-mat-khau/` redirects before switching traffic.

Keep email confirmations enabled.

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

The organization is on Supabase Free. The default hosted sender is testing-only and is not the public delivery channel. Before opening registration to arbitrary users, connect a custom SMTP provider and verify its sending domain. Issue #1 tracks this launch gate.

## Production build configuration

The Pages workflow publishes only the Supabase project URL and a browser-safe `sb_publishable_...` key. Never expose a secret/service-role/SMTP key.

Production release sequence:

1. `python -m engine.cli build-public`
2. `python -m unittest discover -s engine/tests -v`
3. `python scripts/build_pages.py --output .pages-site` with auth enabled and public Supabase config.
4. `python scripts/verify_pages_auth.py .pages-site`
5. Only after all checks pass may GitHub Pages deploy.

The workflow uses `cancel-in-progress: true`, so a newer `main` commit cancels stale Pages runs and becomes the only release candidate.

The verifier blocks deployment when production auth is disabled, email-delivery state is not explicitly declared, Supabase config is incomplete, a privileged key appears in public output, or OTP/legal/password-hardening/account-deletion surfaces are missing.

## Implemented flows

- Signup: email + password + terms/privacy consent.
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
- RLS restricts profile reads to the signed-in user and does not let the browser edit entitlement fields.
- Database grants are least-privilege: `anon` has no direct table privileges; `authenticated` receives only `SELECT` on `profiles`, with RLS restricting rows to the signed-in user. `consent_receipts` is not directly granted to browser roles.
- Versioned terms/privacy consent receipts in `public.consent_receipts` created by the server-side signup trigger.
- Public Terms and Privacy pages.
- Self-service account deletion requires current-password reauthentication plus explicit `XOA` confirmation before the authenticated Edge Function is invoked.
- `delete-account` Edge Function uses the current Supabase publishable/secret key model, keeps server-only secret material inside Supabase, validates the user JWT, restricts browser origins, and deletes related profile/consent rows through database cascades.
- Global login/register or account/logout controls on deployed HTML pages.

## Security boundaries

- Passwords and OTPs are never sent to StockRadar market-data/analytics endpoints.
- Pending signup email is stored only in session storage for UX continuity; password and OTP are not persisted there.
- Public Pages code may contain only the Supabase project URL and publishable key.
- Secret/service-role/SMTP credentials remain server-side only.
- Paid entitlement must come from trusted backend/billing state, never client-editable metadata.
- Never collect broker passwords, trading OTPs, broker API secrets, order credentials, NAV, bank OTPs, or portfolio-control credentials through StockRadar authentication.

## Release checks after Auth changes

- GitHub Actions regression suite: PASS.
- Production auth artifact verifier: PASS.
- Supabase Security Advisor: no unresolved warnings introduced by the change.
- Supabase Performance Advisor: no unresolved warnings introduced by the change.
- Verify effective browser grants remain least-privilege after schema changes.
- Test one real signup mailbox end to end after any email-template, SMTP, Site URL, redirect, or canonical-domain change.
