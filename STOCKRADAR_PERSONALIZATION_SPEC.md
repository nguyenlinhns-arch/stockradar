# StockRadar Personalization Specification V2.1.2

## Purpose

Personalization serves one of six product values; it is not individualized order advice. It prioritizes existing research by the horizons, sectors and tickers a user selected.

## Onboarding

Ask only three groups after signup: one or more horizons, up to three sectors, and up to three watchlist tickers. Do not ask for broker identity, NAV, price paid, OTP or trading authority. `owns_stock` is an optional user-declared boolean used only to choose the holding view.

## Watchlist entitlement

| Tier | Limit | Product email |
| --- | ---: | --- |
| Public | 0 | none |
| Free | 3 | none; transactional only |
| Trial 7 days | 3 | verified + consented |
| Paid | approximately 20 | verified + consented |

Adding an existing ticker is idempotent. The service deduplicates monitoring by ticker, produces one state/event and fans notifications out to eligible subscribers.

## Email ordering

Items are prioritized by watched ticker, then preferred horizon, then preferred sector. Market state and material platform-wide changes may precede personalization. Missing preferences fall back to neutral product ordering; the system does not invent preferences.

## Privacy and controls

Preferences have updated time, access/deletion/withdrawal support and purpose limitation. Analytics may use public ticker and coarse preference dimensions but never transmit private holdings, portfolio value or free text. Production remains blocked until auth, privacy operations and consent evidence exist.
