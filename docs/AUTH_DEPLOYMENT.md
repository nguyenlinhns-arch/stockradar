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

## Email templates

StockRadar uses a 6-digit email OTP for signup verification. In **Authentication → Email Templates → Confirm signup**, use the versioned repository template:

- `supabase/email-templates/confirm-signup.html`

The template must contain `{{ .Token }}`. If the confirmation template only contains `{{ .ConfirmationURL }}`, Supabase sends a link instead of the six-digit OTP expected by the signup UI.

For password recovery use:

- `supabase/email-templates/recovery.html`

Before sending verification/recovery traffic at scale, configure a production SMTP provider in Supabase Auth. Supabase's built-in sender is suitable for early testing but should not be treated as the production delivery channel.

## Production build configuration

The Pages workflow publishes only the Supabase project URL and a browser-safe `sb_publishable_...` key. Never expose a secret/service-role key.

Production release sequence:

1. `python -m engine.cli build-public`
2. `python -m unittest discover -s engine/tests -v`
3. `python scripts/build_pages.py --output .pages-site` with auth enabled and public Supabase config.
4. `python scripts/verify_pages_auth.py .pages-site`
5. Only after all checks pass may GitHub Pages deploy.

The verifier blocks deployment when production auth is disabled, Supabase config is incomplete, a privileged key appears in public output, or OTP/legal/account-deletion surfaces are missing.

## Implemented flows

- Signup: email + password + terms/privacy consent.
- Signup confirmation: six-digit email OTP using `verifyOtp`.
- Resend signup OTP with a persistent 60-second UI cooldown plus Supabase server-side rate limiting.
- Resume verification from the login page for users who registered but have not confirmed their email.
- Sign in with email + password.
- Persistent managed session and automatic token refresh.
- Sign out.
- Forgot-password email and reset page.
- Change password while signed in.
- User profile in `public.profiles`: default tier `FREE`; status moves from `PENDING` to `ACTIVE` after email verification.
- RLS restricts profile reads to the signed-in user and does not let the browser edit entitlement fields.
- Versioned terms/privacy consent receipts in `public.consent_receipts` created from signup metadata.
- Public Terms and Privacy pages.
- Self-service account deletion through authenticated Supabase Edge Function `delete-account`; related profile and consent rows cascade on Auth user deletion.
- Global login/register or account/logout controls on deployed HTML pages.

## Security boundaries

- Passwords and OTPs are never sent to StockRadar market-data/analytics endpoints.
- Pending signup email is stored only in session storage for UX continuity; password and OTP are not persisted there.
- Public Pages code may contain only the Supabase project URL and publishable key.
- Paid entitlement must come from trusted backend/billing state, never client-editable metadata.
- Never collect broker passwords, trading OTPs, broker API secrets, order credentials, NAV, bank OTPs, or portfolio-control credentials through StockRadar authentication.

## Release checks after Auth changes

- GitHub Actions regression suite: PASS.
- Production auth artifact verifier: PASS.
- Supabase Security Advisor: zero unresolved auth-schema warnings introduced by the change.
- Test one real signup mailbox end to end after any email-template, SMTP, Site URL, redirect, or canonical-domain change.
