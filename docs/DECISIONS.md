# Decision Log

## D-001 — Project source of truth

StockRadar project files are the source of truth. The old GPT is a client/regression harness, not the product core.

## D-002 — Narrow V1

Build only `HOSE → SCORE → STATE → RADAR 5` plus Track Record, alerts contract and acquisition pages.

## D-003 — Python standard-library core

Use dependency-light Python and SQLite so rules/tests run immediately in the available environment. A production service can wrap the same contracts later.

## D-004 — MOCK must fail production claims

MOCK is a Data Grade, not a visual note alone. The full-universe gate rejects it even when fixture coverage is 100%.

## D-005 — Local backend, deployment later

Lead/event collection works locally. Production hosting and privacy operations remain blocked rather than being simulated as live.

## D-006 — Ads winner requires D7

The seven-day spend period is followed by a retention observation period. No winner is selected on CTR alone.

## D-007 — Brand due diligence

Proceed with the user-chosen StockRadar name, but require trademark/confusion review because similar international financial brands exist.

## D-008 — Four horizons and conditional Top 10 supersede D-002

The current master specification expands the ranking contract to Short, Medium, Long and Accumulation, each with a separate Top 10 and future sector × horizon view. The existing five-item MOCK engine remains a validation fixture only; it is not the production product claim. Knowledge is allowed only when it directly explains methods used by StockRadar and does not become a newsroom.
