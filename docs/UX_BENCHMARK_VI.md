# Vietnam finance-product UX benchmark

Updated: 2026-09-01 UTC

## Purpose

This review extracts product-structure patterns from established Vietnamese finance websites. It does not copy their visual design, wording, datasets or proprietary tools. Every adopted pattern is narrowed to StockRadar's positioning:

`HOSE scan → goal-specific ranking → clear thesis/risk → state-change alert → immutable result`

## Observed patterns and decisions

| Product | Public pattern observed | Adopted for StockRadar | Deliberately excluded |
| --- | --- | --- | --- |
| [FireAnt](https://www.fireant.vn/Guide/Detail/263) | Technical-analysis tools are linked to alerts, statistics and reuse workflows. Its public guide exposes a task-oriented learning hierarchy. | Cross-link each method to the Radar state it informs; make alerts a primary task; provide related-learning links. | Realtime charting, dozens of drawing tools, social feed and indicator library. |
| [FiinTrade](https://web.fiintrade.vn/nhom-trang-tinh-nang/chien-luoc-dau-tu/xep-hang-co-phieu/) | Ranking can be viewed by industry or stock group, with alternate ranking/criteria views. | Preserve the planned `sector × investment horizon` model; explain which evidence each ranking uses. | Terminal-style dashboards and broad data exploration in V1. |
| [Simplize](https://simplize.vn/about-us) | The product promise centers on simplifying stock discovery and analysis; its learning area organizes foundational knowledge and risk. | A dedicated Knowledge hub, plain Vietnamese, short summaries, method limitations and reading paths. | Course marketplace, general personal-finance curriculum and content volume unrelated to StockRadar. |
| [SSI iBoard](https://www.ssi.com.vn/khach-hang-ca-nhan/nen-tang-giao-dich/nen-tang-giao-dich-web-trading/iboard-web) | High-frequency tasks are integrated and personalized; alerts reduce the need to watch the screen continuously. | Persistent task navigation, mobile menu, state-change alert proposition and future watchlist scope. | Order entry, broker integration and multi-asset trading. |
| [VietstockFinance](https://finance.vietstock.vn/) | Clear taxonomy across market, sector, company, stock and investment tools; glossary/learning sits beside data. | Method taxonomy and a matrix connecting method, question, engine stage and limitation. | Newsfeed, macro-data warehouse, export terminal and a general-purpose screener. |
| [CafeF Data](https://cafef.vn/du-lieu.chn) | Market data is grouped into market map, industry filters, company lookup, reports and event calendars. | Future sector navigation and explicit event-risk gate; clear public data disclaimers. | Newsroom, continuous news aggregation and broad market-data portal. |

## Implemented changes

- Reframed the homepage around four investment horizons: Short, Medium, Long and Accumulation.
- Added an accessible mobile navigation menu focused on Radar, Knowledge, Alerts, Results and PRO.
- Added a Knowledge hub plus six method guides:
  - CANSLIM, SEPA and VCP;
  - Volume Price Analysis;
  - 4M and margin of safety;
  - Pocket Pivot and early momentum;
  - Trend, Stage Analysis, Ichimoku and Bollinger;
  - risk management and R-multiples.
- Added the same article structure to every guide: quick explanation, method mechanics, StockRadar application, failure modes, sources and related reading.
- Updated public pricing language to the specification: 299,000 VND per 30 days planned standard price; 199,000 VND per 30 days initial test price; still not open for sale.
- Replaced personalized public copy with neutral user-facing Vietnamese.

## Content and copyright rule

Knowledge pages are original StockRadar explanations. They attribute authors and books, link to official/public references where useful, and do not reproduce chapters, charts, examples or long passages. Any numeric rule from a book remains a hypothesis until it is validated against an appropriate HOSE dataset.

## Validation targets

- All knowledge routes resolve locally and in the static GitHub Pages artifact.
- All pages include a title, description, mobile viewport and valid internal links/assets.
- Knowledge pages expose method, limitation, StockRadar application and bibliography sections.
- No public asset contains the previous personal brand.
- GitHub Pages remains `noindex,nofollow` while data, privacy, compliance and custom-domain gates are open.
