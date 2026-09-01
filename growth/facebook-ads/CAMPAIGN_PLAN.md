# Facebook Ads Validation Plan — 3–5 triệu đồng

## Goal

Find the proposition with the best activated-user economics and retention. Do not optimize for likes, cheap video views or CTR alone.

## Fair-test structure

Campaign: `SR_PROP_TEST_V1`  
Budget type: ad-set budget so each proposition receives equal spend.  
Audience: the same eligible Vietnam audience for all three ad sets.  
Placements: the same automatic/eligible placements for all three, verified in the live account.  
Optimization: landing-page view or completed lead, depending on whether the deployed conversion event has enough reliable volume.

| Ad set | Daily media | Days | Media subtotal | Creatives | Landing |
| --- | ---: | ---: | ---: | --- | --- |
| RADAR5 | 150.000đ | 7 | 1.050.000đ | R5-A, R5-B | `/radar5` |
| BREAKOUT | 150.000đ | 7 | 1.050.000đ | BO-A, BO-B | `/breakout` |
| RISK | 150.000đ | 7 | 1.050.000đ | RR-A, RR-B | `/risk` |

Base media: **3.150.000đ**.

Meta's current Vietnam VAT help page states a 10% VAT rate for Meta ads in Vietnam, so the planning cash outlay is about **3.465.000đ** if that rate applies to the account at billing. Verify the actual invoice/account before launch. The remaining envelope up to 5 million is a reserve for one controlled winner-validation round, not automatic scale.

## Timeline

- D-3 to D-1: production domain, pixel/event QA, policy/account verification, mobile speed and form tests.
- D0: publish all three ad sets at the same time.
- D0–D3: avoid creative/budget edits unless tracking/policy is broken.
- D4–D7: pause only clearly broken ads; log every change.
- D8–D14: retention observation. A D7 winner cannot be known at the end of media day 7.
- D15: select winner, inconclusive result or second test.

## Activation definition

An activated user completes signup and, in the first session/day, performs at least one of:

- `radar_view` + `track_record_view`;
- `top5_expand`;
- `alert_opt_in`.

## Decision hierarchy

1. Cost per activated user.
2. D7 retention.
3. D1 retention.
4. Alert opt-in.
5. PRO intent.
6. Paid conversion/CAC only after payment is legitimately enabled.
7. Qualitative feedback.

CTR/CPC diagnose the creative. They do not choose the product.

## Pre-launch policy gate

Meta's official [financial-services ad policy](https://transparency.meta.com/policies/ad-standards/restricted-goods-services/financial-services/) says financial advertisers may need business/identity verification and evidence of authorization. Confirm the actual account's requirements before spending. Do not bypass a requested authorization gate.

Creative rules:

- no guaranteed or risk-free language;
- no “win probability = score”;
- no ticker-specific “buy now” claim;
- no fabricated track record;
- landing and creative disclaimers must be consistent;
- form does not ask for financial-account credentials or OTP.

## Stop conditions

- broken/missing events;
- landing page shows MOCK as live data;
- Meta requests authorization that is not available;
- legal/compliance review rejects planned copy;
- abnormal/bot traffic dominates;
- spend exceeds the approved envelope.

## Winner-validation reserve

Use 850.000–1.535.000đ only after a provisional winner exists. Run one new creative against the winning proposition while holding audience/landing constant. If no proposition has meaningful activation/retention, preserve the reserve and revise the product promise instead.

