# StockRadar authentication deployment

StockRadar uses GitHub Pages for the public site, so passwords must not be handled by the static site itself. The browser integration is wired to Supabase Auth with email/password and fails closed until the public Supabase project configuration is supplied.

## Production configuration

1. Create or select the StockRadar Supabase project.
2. In **Authentication → URL Configuration**, set the production Site URL and allow redirects to:
   - `/tai-khoan/`
   - `/dat-lai-mat-khau/`
3. Keep email confirmation enabled for public signups.
4. Before sending real verification/recovery traffic at scale, configure a production SMTP provider in Supabase Auth.
5. In the GitHub repository **Settings → Secrets and variables → Actions → Variables**, add:
   - `STOCKRADAR_SUPABASE_URL`
   - `STOCKRADAR_SUPABASE_PUBLISHABLE_KEY`
6. Re-run the Pages workflow. `scripts/build_pages.py` writes these public values into the deployed `assets/auth-config.js`.

The publishable/anon key is intended for browser use. Never place a Supabase secret key or service-role key in GitHub Pages, repository variables exposed to the build artifact, JavaScript, or HTML. The build fails if a clearly privileged key is detected.

## Implemented flows

- Sign up with email + password.
- Email verification redirect to `/tai-khoan/`.
- Sign in with email + password.
- Persistent managed session + automatic token refresh.
- Sign out.
- Forgot-password email.
- Password recovery at `/dat-lai-mat-khau/`.
- Change password while signed in.
- Account page showing email, verification status and creation date.
- Global login/register or account/logout controls injected into every deployed HTML page.

## Security boundaries

- Passwords are passed only to the managed authentication SDK and are never sent to StockRadar analytics or market-data endpoints.
- The account page's `FREE` label is presentation only. Paid entitlements must later come from a trusted billing/backend source and must never be authorized from client-editable metadata.
- Do not collect broker passwords, trading OTPs, broker API secrets, order credentials, NAV, or portfolio-control credentials through this auth flow.
