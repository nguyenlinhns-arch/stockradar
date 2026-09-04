# StockRadar Premium Email Product V1

## Product promise

Premium email is not a longer newsletter. It is the delivery surface for a monitoring service:

> StockRadar follows the tickers the user cares about and brings the meaningful decision change to the inbox so the user does not need to keep reopening the website.

## Buyer journey

1. User upgrades to Premium.
2. User confirms email and chooses which email products to receive.
3. User adds watchlist tickers, horizon and whether the ticker is already owned.
4. User enables alert delivery only for the subset that matters most.
5. StockRadar checks the eligible state at scheduled checkpoints.
6. No material state change means no standalone action alert.
7. A confirmed change produces an action-first email linked to the latest ticker state.
8. Email history remains auditable; the sender never recalculates the decision.

## Premium 09:00 report

The report is watchlist-first, not market-news-first.

Order:

1. **What in my watchlist needs attention today?**
2. **What changed since the previous eligible report?**
3. **Which owned positions have risk/action changes?**
4. **Which watched-but-not-owned tickers have an actionable change?**
5. **Market context** in a compact form.
6. **Eligible opportunities outside the watchlist**, if any.
7. **Risk list** and direct audit/report links.

Dynamic subject examples:

- `[StockRadar] 2 mã cần chú ý hôm nay · 04/09`
- `[StockRadar] Watchlist ổn định · chưa cần hành động · 04/09`

A stable watchlist is a legitimate result. The report should explicitly say that StockRadar checked and found no new action rather than creating artificial activity.

## Premium intraday action alert

Standalone action alerts are for confirmed material changes only.

Priority:

- `P0`: SELL / invalidation / stop / material portfolio risk.
- `P1`: REDUCE / material deterioration.
- `P2`: BUY / ADD when the action gate is satisfied.
- `P3`: lower-urgency watch changes; normally digest rather than push-style mail.

Subject is action-first and readable from the phone lock screen:

- `[StockRadar] HPG · CHỜ → MUA | 10:30`
- `[StockRadar] VCI · GIỮ → GIẢM | 13:30`
- `[StockRadar] FPT · GIỮ → BÁN | 14:15`

Body order:

1. Ticker and old state → new state.
2. Evaluation timestamp and reference price.
3. New-position decision.
4. Existing-holding decision when ownership context is known.
5. Buy Zone / Stop / Target / Risk-Reward where applicable.
6. 2–4 strongest reasons.
7. Explicit invalidation condition.
8. Next scheduled review.
9. Late-open notice and link to the latest state.

For BUY/ADD, the email must say that the action is tied to the stated action zone. If the price has already left that zone, the reader must check the current state and must not treat the old email as a permanent instruction to chase price.

## Ownership context

Watchlist personalization is not cosmetic.

The same ticker may produce different useful output for two users:

- User does not own it → `BUY / WAIT` is primary.
- User already owns it → `HOLD / ADD / REDUCE / SELL` is primary.

The email sender must never infer ownership. It uses the account's declared watchlist context only and does not store cost basis.

## User-controlled email products

- Daily 09:00 report.
- Intraday action alerts.
- Post-session digest (optional).
- Weekly review (optional).

No product is enabled without valid consent. A user may disable one email product without disabling the others. `Unsubscribe all` remains available.

## Delivery health shown to the user

My StockRadar should expose a simple health summary:

- Email verified.
- Account tier/status.
- Daily report preference.
- Action-alert preference.
- Active watchlist count.
- Tickers with per-ticker alert enabled.
- Production delivery system ready/not ready.
- Last email kind/status/time when available.
- Active suppression state if one exists.

This summary contains only the current user's metadata and never exposes provider secrets or another user's email/content.

## Non-negotiable consistency rules

- Email never calculates a stock decision independently.
- Email state, price map and timestamps must match the immutable StockRadar decision record used by the website.
- Older alerts must never overwrite or arrive as if they were newer than a later confirmed state.
- No material state change = no standalone action alert.
- Stale, insufficient, unlicensed or otherwise ineligible data suppresses product email.
- A failed/invalidated prior decision stays in history; it is not rewritten to make performance look better.
- Sender activation remains fail-closed until provider, sender domain, unsubscribe, bounce/complaint, consent/compliance and delivery controls are all proven ready.
