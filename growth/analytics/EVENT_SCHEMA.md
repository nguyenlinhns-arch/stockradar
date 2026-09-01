# Analytics Event Contract V2.1.2

Required envelope: `event_name`, `occurred_at` (ISO 8601), `session_id`, `page`, `proposition`, `utm`, `properties`.

## Canonical product events

| Event | Fires when | Required context |
| --- | --- | --- |
| `top_view` | a ranked list is rendered | horizon, data grade, mock/live |
| `horizon_change` | user changes target horizon | from, to |
| `sector_view` | sector surface opens | horizon when known |
| `recommendation_list_view` | recommendation lifecycle table renders | mode, mock/live |
| `performance_view` | performance surface renders | total published, mode |
| `stock_search` | normalized ticker search is submitted | ticker |
| `ticker_input_started` / `ticker_autocomplete_selected` | lookup intent and master selection | ticker/query class, never free text |
| `ticker_search_valid` / `ticker_search_invalid` | security-master validation completes | ticker, master snapshot, status |
| `ticker_cache_hit` / `ticker_cache_miss` | deep-report cache is checked | ticker, horizon, report version |
| `quick_report_view` / `full_report_requested` | user advances from quick to deep result | ticker, data grade, freshness |
| `four_horizon_view` / `holding_view` | value proof renders | ticker, public/Free/Trial/Paid |
| `today_changes_view` | meaningful-diff view renders | mode, change count |
| `onboarding_*` | one of three onboarding groups changes | controlled horizon/sector/ticker only |
| `sample_premium_report_view` | full sample report renders | ticker, mock/live |
| `signup_start` | first meaningful signup interaction | proposition |
| `signup_complete` | server accepts or recognizes signup | proposition |
| `pro_view` | Advanced comparison opens | price variant |
| `checkout_start` | real checkout session is created | plan, amount, currency |
| `payment_complete` | provider webhook verifies payment | plan, amount, currency |
| `email_open` | email provider reports an open | message type, campaign |
| `email_click` | signed email link is clicked | message type, destination |
| `renewal_complete` | verified payment extends entitlement | plan, new expiry |

Legacy V1 names remain allowlisted only for backward-compatible dashboards while clients migrate. New reports use the canonical V2 names.

## Funnels

Acquisition: `landing_view → ticker_search_valid → quick_report_view → four_horizon_view/holding_view/recommendation_history_view → signup_start → signup_complete`.

Commercial: `pro_view → checkout_start → payment_complete → renewal_complete`.

Engagement: `email_open → email_click → recommendation_list_view/sample_premium_report_view`.

## Quality and privacy

- server confirmation is mandatory for signup, checkout, payment and renewal;
- deduplicate retries by event/idempotency key;
- exclude internal and QA traffic from product decisions;
- retain raw events separately from derived funnels;
- never send broker credentials, OTP, password, transcript, holdings or portfolio value;
- record `is_mock` and `record_mode` so SHADOW traffic cannot be reported as production adoption.
