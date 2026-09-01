# Priority Radar (legacy route: Radar 5)

Job: reduce the time and cognitive load of searching the HOSE universe.

Output fields:

- horizon, rank, ticker and evidence score/coverage;
- setup and current state;
- change from prior snapshot;
- recommendation date, buy zone, target/fair value, invalidation and current price;
- market regime;
- Data Grade, universe Coverage and timestamp;
- concise thesis, main risk and thesis-change condition.

`/radar5` remains the transitional public route and the current MOCK preview contains five rows. The production target is a separate conditional Top 10 for Short, Medium, Long and Accumulation, plus sector × horizon views. “Top 10 HOSE” must disappear when the full-universe or selected-horizon gate fails.

Activation event: `radar_view` followed by a method view, result-history view or alert opt-in in the same first session. `top5_expand` remains a legacy analytics event until the Top 10 migration is complete.
