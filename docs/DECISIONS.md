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

