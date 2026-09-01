# StockRadar Subscription Specification V2

## Plans

Free and Advanced only. Advanced standard price is planned at 299,000 VND per 30 days; founding test price is 199,000 VND per 30 days. Prices are hypotheses until approved and legitimately enabled.

## Entitlement

Verified payment creates an append-only 30-day grant. Renewal extends from the later of current expiry or verified payment time by exactly 30 days. Expiry downgrades to Free without deleting identity, consent history, recommendation history or watchlist.

## Required states

`FREE`, `CHECKOUT_PENDING`, `PAYMENT_VERIFIED`, `ADVANCED_ACTIVE`, `PAST_DUE`, `EXPIRED`, `REFUNDED`, `CHARGEBACK`. Client redirects never verify payment; provider webhook plus idempotency does.

## Controls

Display plan, grant start/expiry, remaining days, price/currency, renewal status, invoice/reference, refund path and support contact. Require secure auth, verified email, signed webhooks, reconciliation, access-control tests, privacy retention, tax/invoice review and compliance approval.

GitHub Pages has no checkout or entitlement writes. Billing remains BLOCKED and no public CTA may imply payment is live.
