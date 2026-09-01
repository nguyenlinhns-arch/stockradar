# Breakout Radar

Job: surface setups near a valid trigger before price becomes extended.

Preferred states:

- `NEAR_TRIGGER`
- `READY`

Required evidence for a production alert:

- pivot/trigger with timestamp;
- price distance and extension;
- same-time RVOL or documented intraday projection;
- Market Regime;
- liquidity, event and corporate-action checks;
- stop/invalidation and same-horizon R:R when action language is used.

Breakout Radar never upgrades an extended high-score candidate into READY.

