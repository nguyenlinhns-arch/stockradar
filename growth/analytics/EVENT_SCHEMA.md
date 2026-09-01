# Analytics Event Contract V1

Required envelope:

- `event_name`
- `occurred_at` in ISO 8601
- `session_id`
- `page`
- `proposition`
- `utm`
- `properties`

| Event | Fires when | Key properties |
| --- | --- | --- |
| `ad_click` | tracked CTA click where available | creative/content |
| `landing_view` | page initialized | proposition, UTM |
| `radar_view` | Radar JSON rendered | status, is_mock |
| `top5_expand` | user expands evidence/details | ticker, rank |
| `track_record_view` | history rendered | is_mock, snapshot |
| `knowledge_view` | Knowledge hub initialized | page |
| `method_view` | method guide initialized | method |
| `horizon_select` | user opens a horizon explanation | target |
| `signup_started` | first meaningful form interaction | proposition |
| `signup_completed` | backend accepted/recognized lead | proposition |
| `alert_opt_in` | accepted lead chose alerts | proposition |
| `pro_page_view` | PRO page initialized | proposition/UTM |
| `trial_started` | a real trial entitlement is created | plan, price_test |
| `subscription_started` | payment + entitlement confirmed | plan, amount, currency |
| `return_d1` | same identity/session family returns after 24h | first_seen |
| `return_d7` | returns after 7 days | first_seen |

The local website implements all client events except entitlement/payment creation. Trial/subscription events must never fire from a lead form.

## Funnel

Primary: `landing_view → radar_view → signup_started → signup_completed → alert_opt_in → return_d1 → return_d7 → pro_page_view → trial_started → subscription_started`

Education-assisted: `landing_view → knowledge_view → method_view → radar_view`

## Quality checks

- deduplicate client retries with event ID in production;
- exclude internal/QA traffic;
- validate event names server-side;
- use server confirmation for signup/trial/payment;
- retain raw event and derived funnel separately;
- reconcile Ads platform conversions with first-party events;
- never send broker credentials, OTP, transcript or portfolio values as analytics properties.
