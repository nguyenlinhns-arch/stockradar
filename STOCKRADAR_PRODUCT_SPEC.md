# STOCKRADAR PRODUCT SPEC V1.2

Version: 1.2  
Status: public validation website with MOCK-labelled data; production data/auth/email/billing blocked  
Brand: **STOCKRADAR** / **stockradar.vn**

## 1. Product outcome

StockRadar solves one job:

> Quét HOSE → xếp hạng cổ phiếu theo mục tiêu đầu tư → nêu vùng giá, luận điểm và rủi ro → báo khi trạng thái thay đổi.

Homepage promise:

> Quét HOSE. Chọn lọc cổ phiếu phù hợp với mục tiêu đầu tư của bạn.

V1 is a focused decision-support product, not a terminal, price board, newsroom or generic chatbot.

## 2. Four investment horizons

The same stock can receive different conclusions by horizon. A universal score is prohibited.

| Horizon | Reference period | Primary evidence | Required output |
| --- | --- | --- | --- |
| Short | 5–20 sessions | trend, relative strength, VPA, breakout/pivot, volume, extension, liquidity, event risk, market regime | buy zone, target, invalidation/stop, validity period |
| Medium | 1–6 months | trend, growth, industry, flow, business quality, valuation, events | buy zone, target, risk rule, horizon, thesis |
| Long | 6–18 months | business quality, durable growth, moat, management, industry, cash flow, valuation | reasonable buy zone, fair-value range, risks, thesis-change conditions |
| Accumulation | 2–5+ years | business quality, moat, management, balance sheet, cash flow, dividends, fair value, margin of safety | attractive/reasonable/expensive zones, accumulation thesis, stop/exit conditions |

Technical short-term stops must not be copied mechanically into Long or Accumulation recommendations.

## 3. V1 product surfaces

Included or specified:

1. Home organized around the four horizons.
2. Top 10 HOSE for each horizon, subject to the full-universe gate.
3. Sector × horizon rankings.
4. Stock-detail page with four horizon tabs.
5. Active recommendations with recommendation price, current price, target, invalidation and status.
6. Trigger Radar and Risk Radar.
7. Immutable result history and corrections.
8. Watchlist for paid users.
9. Email as the primary alert channel.
10. Free/Advanced 30-day subscription model.
11. Knowledge hub that explains the methods and their limitations.
12. Analytics/UTM and acquisition experiment contracts.

Current public implementation includes Home, a five-item MOCK Radar preview, sector matrix shell, stock search, a four-horizon DEMO1 report, active-recommendation records, Trigger Radar, Risk Radar, email schedule, watchlist/account contracts, Result History, Knowledge, pricing scope and a disabled-on-Pages signup form. Search, watchlist, auth, email and billing remain visibly blocked wherever a production backend or licensed data is required.

Excluded from V1:

- realtime price board or charting terminal;
- newsfeed/newsroom or social network;
- hundreds of user-configurable indicators;
- native mobile app;
- complex portfolio management;
- broker integration or order placement;
- generic AI chatbot;
- uncalibrated price/win-probability prediction;
- more than Free and Advanced service tiers.

## 4. Three user jobs

| Surface | User job | Primary hypothesis | Current route |
| --- | --- | --- | --- |
| Priority Radar | Reduce search overload | A short, goal-specific ranked list creates acquisition | `/radar5` (transitional route) |
| Trigger Radar | Improve timing | Users value seeing setups before they become extended | `/breakout` |
| Risk Radar | Avoid stale theses | Material state deterioration creates retention | `/risk` |

No hypothesis wins before real activation, D7 retention and Advanced intent are observed.

## 5. Recommendation state contract

Internal enums remain stable for API compatibility; public labels are Vietnamese.

| Internal | Public label |
| --- | --- |
| `WATCH` | THEO DÕI |
| `NEAR_TRIGGER` / `WAIT_BUY` | CHỜ MUA |
| `READY` / `IN_BUY_ZONE` | ĐẠT VÙNG MUA |
| `TRIGGERED` / `ACTIVE` | ĐANG CÓ HIỆU LỰC |
| `EXTENDED` | TĂNG QUÁ VÙNG MUA |
| `INVALIDATED` | KHÔNG CÒN ĐẠT ĐIỀU KIỆN |
| `TARGET_REACHED` | ĐẠT MỤC TIÊU |
| `STOP_REACHED` | CHẠM MỨC CẮT LỖ |
| `EXPIRED` | HẾT THỜI HẠN |
| `CLOSED` | ĐÓNG KHUYẾN NGHỊ |

High-value transitions include readiness, activation, invalidation, extension, entering/leaving a ranking and market-regime change. `INVALIDATED → READY` on the same setup identity is rejected; a new thesis requires a new record lineage.

## 6. Top 10 publishing gate

The public label `TOP10_HOSE` is allowed only when:

1. exchange is HOSE;
2. the expected security master is known;
3. scanned count equals expected count;
4. valid + excluded reconciles to expected;
5. every exclusion has a reason;
6. required fields contain no missing/stale records;
7. same-snapshot and adjusted-basis checks pass;
8. trading calendar and corporate actions are reconciled;
9. Data Grade is `DECISION_GRADE`;
10. the selected horizon has at least ten eligible candidates.

Otherwise the result is an incomplete-universe status or a shortlist from available data. MOCK data can never publish a real Top 10 HOSE claim.

The current engine fixture ranks five candidates to exercise legacy gates. Production work must parameterize ranking size and migrate the claim from `TOP5_HOSE` to horizon-specific `TOP10_HOSE` without weakening any gate.

## 7. Four score models

Short, Medium, Long and Accumulation require different weight profiles. Shared evidence definitions are allowed; a universal weighted total is not.

Rules common to all models:

- score measures evidence strength/coverage, not win probability;
- exact score is shown only when score Coverage is complete; otherwise show a range;
- missing evidence is not silently treated as zero or renormalized away;
- the same evidence ID cannot receive full credit in multiple buckets;
- ranking compares candidates from the same snapshot, basis, horizon and framework;
- market regime changes action/priority and can block a new position without rewriting research history.

The engine now contains four distinct validation weight profiles and regression checks that each profile totals 100. They are product-contract implementations, not market-calibrated production models. Release still requires licensed inputs, horizon-matched backtests, out-of-sample calibration and regression evidence.

## 8. Immutable recommendation record

At publication, freeze:

- recommendation/setup ID, ticker and horizon;
- publication date/time and validity period;
- snapshot/source/Data Grade/universe reconciliation;
- rank, evidence score/coverage and state;
- recommendation buy zone and current price at publication;
- target/fair-value range and invalidation condition;
- market regime, key evidence, thesis, main risk and thesis-change conditions.

Later price/performance observations are append-only and contain current price/time, outcome, MAE, MFE and R-multiple where appropriate. Errors create correction records with reason/time; they never overwrite the original release.

## 9. Free and Advanced

Free — **0 VND**:

- Radar after the session;
- market/setup state;
- Knowledge hub;
- public result history;
- basic weekly summary when email is enabled.

Advanced:

- planned standard price: **299,000 VND / 30 days**;
- initial test price: **199,000 VND / 30 days**;
- Top 10 by four horizons and sector × horizon;
- earlier/priority Radar;
- readiness, invalidation, rank-entry/exit and market alerts;
- watchlist and deeper history.

Every payment adds 30 days. Payment remains disabled until data, privacy, security, subscription and Vietnamese compliance gates pass.

## 10. Alert contract

Email is the primary V1 channel. Priority:

- P0 — invalidation/risk/market regime;
- P1 — readiness/trigger;
- P2 — thesis/fundamental event;
- P3 — watch-state improvement.

An alert is not an automatic buy/sell instruction. Every action-oriented alert carries recommendation ID, snapshot, timestamp, horizon, state change, reason, Data Grade and validity boundary. Delivery must be idempotent.

## 11. Knowledge contract

Knowledge content supports product comprehension, not a general newsroom. Each method guide must include:

1. a plain-Vietnamese explanation;
2. the question the method answers;
3. how StockRadar uses it;
4. failure modes and non-claims;
5. attributed books/public sources;
6. related methods.

Current method groups: CANSLIM/SEPA/VCP, VPA, 4M, Pocket Pivot, trend/Stage Analysis/Ichimoku/Bollinger and risk management. Content is original synthesis; books, chapters, charts and examples are not reproduced.

## 12. Success metrics

Primary metrics:

1. cost per activated user;
2. D1 retention;
3. D7 retention;
4. alert opt-in;
5. Advanced intent;
6. paid conversion once legally/technically enabled;
7. CAC feasibility.

CTR and social engagement are diagnostic, not winner metrics.

## 13. Acceptance criteria

Public validation website passes when:

- rules engine/ledger tests pass;
- MOCK is visible and blocked from Top 10 claims;
- all public and Knowledge routes render with valid assets/metadata;
- responsive navigation, horizon positioning and pricing are consistent;
- static Pages build disables writes and remains `noindex,nofollow`;
- blockers remain explicit.

Production V1 additionally requires:

- licensed/current HOSE data and full-universe reconciliation;
- four validated horizon score models and Top 10/sector rankings;
- stock-detail/active-recommendation/watchlist flows connected to live data and authenticated persistence;
- authentication, production database and privacy operations;
- scheduler and idempotent email delivery;
- 30-day billing/subscription lifecycle;
- formal Vietnamese legal/compliance review;
- at least one complete live/shadow snapshot through the shipping gate.
