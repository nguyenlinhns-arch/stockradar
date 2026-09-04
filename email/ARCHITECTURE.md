# Email Architecture Contract

Status: signup/consent and pre-auth interest capture foundations implemented; no production sender is connected.

## Buyer-first product principle

A paid user does not buy an email because it contains more indicators. The email is valuable only when it reduces the time and ambiguity between **a meaningful state change** and **the user's next decision**.

Every Premium action alert therefore follows this order:

1. **What changed?** — the material state transition since the previous eligible scan.
2. **New position?** — `BUY` / `WAIT` for a user who does not own the ticker.
3. **Existing holding?** — `HOLD` / `ADD` / `REDUCE` / `SELL` for a user who already owns it when that context is known.
4. **Action map** — Buy Zone/current reference, position guidance when available, Stop/invalidation, Target and Risk/Reward.
5. **Why now?** — the 2–4 strongest reasons, not a dump of every indicator.
6. **What would invalidate this?** — the specific condition that would change the decision.
7. **Evidence timestamp** — ticker, horizon, report date, market-session reference, data cutoff and generated time.

Methods such as 4M, CANSLIM, SEPA/VCP, VPA/RVOL and valuation support the decision but appear **after** the decision fields. A user should be able to understand the action and risk without reading a long methodology section.

## Entitlement gate

Transactional account mail is available where required for every account tier. This includes account verification, password recovery, payment/renewal and other necessary account notices.

**Product-content email is Trial/Paid only.** The entitlement contract is:

- `daily`: Trial/Paid only after email verification and explicit product consent.
- `state_change` / buy-sell event alerts: Trial/Paid only after verification and explicit product consent.
- `post_session` and `weekly`: Trial/Paid only.
- Free may store Premium interest before upgrade, but it cannot enable product-content delivery.

This separation is mandatory. Preference data is not delivery entitlement, and a Free account must remain unable to convert saved interest into a product email until the account tier becomes Trial/Paid.

## Pre-auth email interest path

While production Auth SMTP remains closed, the public website may collect a minimal pending Premium-interest request without pretending that signup or delivery is complete.

1. The visitor enters an email and may explicitly select Premium `DAILY_BRIEF`, `EVENT_ALERT`, or both. Nothing is pre-checked.
2. The visitor explicitly accepts the current privacy/consent version.
3. GitHub Pages calls the public `email-interest` Edge Function. The browser receives no service-role/provider secret.
4. The Edge Function enforces allowed origins, JSON/body limits, a honeypot and a daily-hashed technical request fingerprint for rate limiting.
5. Only the Edge Function's service role may invoke `public.capture_email_subscription_interest`; `anon` and `authenticated` have no direct execute grant.
6. The request is stored in `private.email_subscription_intents` as `PENDING_VERIFICATION` for at most 30 days. It is interest only and never authorizes delivery.
7. A later account flow may retain those choices as preference data, but product email remains disabled until verified Trial/Paid entitlement, current consent and the production delivery gate all pass.

## Delivery windows

| Window | Purpose | Default content |
| --- | --- | --- |
| 09:00 Vietnam time | Premium daily pre-session report | Trial/Paid: watchlist-first decision brief according to available data and entitlement. |
| 10:30 / 11:15 / 13:30 / 14:15 | Confirmed state changes | Trial/Paid: P0 risk/invalidation, then P1 readiness/trigger such as buy/sell actions when the signal gate passes. |
| After session | Freeze the close | Trial/Paid snapshot summary, new/changed/expired recommendations. |
| Weekly | Review process | Trial/Paid state transitions, immutable outcomes and method note. |

These are scheduled scans, not realtime-by-the-second promises. An intraday scan may produce no email when no actionable state change reaches the required gate.

## Daily report contract

Every product email carries separate `report_date`, `market_session_reference`, `data_cutoff_at` and `generated_at` fields. The 09:00 report uses the latest verified data available at generation time. If that data is from the previous trading session, the email must show both dates explicitly.

Canonical daily subject:

`[StockRadar][dd/mm/yyyy] Báo cáo thị trường hàng ngày`

Premium daily content is ordered by decisions rather than by methodology:

1. **Recipient watchlist first** — tickers the user follows, with holding-context priority when declared.
2. **Action changes since the previous report** — new `BUY/WAIT/HOLD/ADD/REDUCE/SELL` states only.
3. **Market regime today** — supportive / neutral / risk-off and the one or two most important reasons.
4. **Top eligible opportunities** — only Decision-Grade setups, never a forced fixed count.
5. **Risk list** — invalidations, stops, material deterioration and expiring setups.
6. **Audit links** — direct links to the ticker report and recommendation history.

The daily report should be skimmable before the session. Long method explanations belong on the website, not above the actionable summary in the inbox.

## Intraday alert contract

Premium action alerts are evaluated at 10:30, 11:15, 13:30 and 14:15 Vietnam time. Only send when the relevant state change is confirmed and all data/entitlement/consent gates pass. Examples include Pocket Pivot, Early Breakout, Confirmed Breakout, Retest/Add-on, Reduce and Stop/Exit.

Example subjects:

- `[StockRadar][dd/mm/yyyy][<MÃ>] MUA MỚI — vào vùng hành động`
- `[StockRadar][dd/mm/yyyy][<MÃ>] HẠ TỶ TRỌNG — rủi ro tăng`
- `[StockRadar][dd/mm/yyyy][<MÃ>] BÁN/CẮT LỖ — điều kiện vô hiệu`

Every intraday action email must contain a compact decision card before any explanation:

| Field | Requirement |
| --- | --- |
| Ticker + horizon | Mandatory |
| What changed | Mandatory and compared with the previous eligible state |
| New-position decision | Mandatory when the model can support it |
| Holding decision | Mandatory when holding context is known and data supports it |
| Current/reference price | Mandatory for a price-dependent action |
| Buy Zone | Mandatory for a buy/add action |
| Stop / invalidation | Mandatory for tactical buy/add actions |
| Target | Mandatory where the horizon contract requires one |
| Risk/Reward | Mandatory where the horizon contract requires one |
| Reasons | 2–4 strongest evidence points |
| Next review | Next scheduled scan or explicit review condition |
| Data timestamps | Mandatory |

A Premium email must never imply that `BUY` for a new position automatically means `ADD` for an existing holder, or that a good long-term business automatically has a valid tactical entry.

## Priority and suppression

- P0: invalidation, stop, material market-regime deterioration.
- P1: enters buy zone, activation, important rank entry/exit.
- P2: thesis/fundamental event.
- P3: watch-state improvement and low-urgency digest material.

Suppress when data is MOCK/STALE/INSUFFICIENT, the state did not materially change, confirmation failed, cooldown is active, consent is missing, the recommendation has expired/closed, or the recipient lacks Trial/Paid entitlement for that product. Free never passes a product-content email entitlement gate.

**No material state change = no action alert.** This is a product requirement, not merely an email-volume optimization. Repeating the same advice at every scan erodes paid-user trust.

## Signup and preference path

Once production Auth email delivery is ready, the account-based funnel is the authoritative path:

1. Signup collects email/password and may collect optional, non-prechecked Premium `DAILY_BRIEF` / `EVENT_ALERT` interest when the user selects Premium intent.
2. Terms/Privacy acceptance and product-email consent are recorded server-side.
3. Email verification activates the account but does not grant product-email entitlement to Free.
4. Trial/Paid may enable selected product emails after verification, consent and delivery-gate checks.
5. Account settings allow preference changes and consent withdrawal.
6. Watchlist rows can store per-ticker `alert_enabled`; this never bypasses Premium entitlement.

Per-ticker alert selection is a buyer-control feature: a Premium user may follow many tickers but only enable push-style action emails for the subset that matters most. The backend must still enforce tier, current consent, global email enablement and signal eligibility.

The browser never becomes the email sender and never holds provider secrets.

## Mandatory production controls

Before enabling actual delivery: verified sender domain; production-grade Auth SMTP; documented consent basis; one-click unsubscribe; suppression list; bounce/complaint handling; rate limits; encrypted secrets; minimal retention; delivery audit; provider webhook verification; disaster disable switch; and Vietnamese legal/privacy review.

GitHub Pages hosts the pending-interest, signup/account and preference UI, but does not send product email itself. Public account signup remains fail-closed while production Auth email delivery is not proven ready. Product email delivery remains disabled until the backend provider/security gate is deliberately opened with evidence.
