# StockRadar Subscription Specification V2.1.3

## Plans

Public, Free, seven-day Advanced Trial and paid Premium/Advanced. Standard price is planned at 299,000 VND per 30 days; founding test price is 199,000 VND per 30 days. Prices remain hypotheses until approved and legitimately enabled.

## Entitlement

Verified payment creates an append-only 30-day grant. Renewal extends from the later of current expiry or verified payment time by exactly 30 days. Expiry downgrades to Free without deleting identity, consent history, recommendation history or watchlist.

The paid promise is continued filtering, evaluation, monitoring, reminders, personalization, journal and P/L maintenance during those 30 days—not a one-time website-access token. Trial expires after seven days and does not convert without an explicit verified payment.

## Checkout UX

The first production payment method is VietQR / bank transfer, optimized for mobile. The checkout page must keep the complete payment task on one screen whenever practical:

1. Show Premium 30-day plan, price, no-auto-renewal rule and the account that will receive the entitlement.
2. Show QR plus bank name, account number, account holder, exact amount and a server-issued unique payment reference.
3. Provide copy controls for account number and payment reference.
4. After the user reports a transfer, move the UI to a pending-verification state. A client-side button or redirect never creates paid entitlement.
5. Only verified backend payment evidence may create a 30-day grant.
6. If checkout is not safely enabled, hide payment destination details and disable the transfer-confirmation action rather than implying payment is live.

The visual language should match StockRadar: navy/white portal shell, red primary action, compact cards, strong amount/reference hierarchy, and a mobile sticky action. The interaction pattern may reuse lessons from earlier internal checkout work, but customer-facing copy and branding must remain StockRadar-specific.

## Required states

`FREE`, `TRIAL_ACTIVE`, `TRIAL_EXPIRED`, `CHECKOUT_PENDING`, `PAYMENT_VERIFIED`, `ADVANCED_ACTIVE`, `PAST_DUE`, `EXPIRED`, `REFUNDED`, `CHARGEBACK`. Client redirects never verify payment; provider webhook or equivalent verified reconciliation plus idempotency does.

## Controls

Display plan, grant start/expiry, remaining days, price/currency, renewal status, invoice/reference, refund path and support contact. Require secure auth, verified email, signed/verified payment evidence, reconciliation, access-control tests, privacy retention, tax/invoice review and compliance approval.

GitHub Pages has no entitlement writes. Billing remains fail-closed until the private billing gate is enabled; no public CTA may imply a payment is accepted while that gate is closed.
