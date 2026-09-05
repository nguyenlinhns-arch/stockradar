# Radar research screen — 05/09/2026

## Cause and behavior

The previous `/radar5/` route read an intentionally empty public action feed and
then legacy scripts replaced the table with an unavailable-data panel. The new
route reads the current research cache through `get_stockradar_radar_v1` for an
active signed-in Free/Premium account. Guest users get an explicit login state.
No static copy of the internal research cache is published.

At verification: 405 HOSE observations dated 04/09/2026, 105 research-ready,
5 initial technical setups, and 0 newly approved buys. Initial setups do not
become buy recommendations. Existing emailed DCM/VHM recommendations remain in
the separate verified ledger and are not erased when the current setup changes.

The screen supports ticker (including L10), sector and state filtering, alternate
sorting, sector leaders, paging, refresh, and four evidence panels per ticker.
The technical panel uses the closing-session volume and previous 20-session
average, not the intraday projection. Price comparisons name both values and the
percentage denominator. Missing values remain absent, not zero.

## Access and data boundaries

The RPC has an explicit `auth.uid()` and active-profile check, an empty search
path and explicit schema qualification. EXECUTE is granted only to authenticated
users; anon/PUBLIC have no access and private table grants remain unchanged.
Only the selected research fields are returned: no raw history, source locations,
recipient data, private portfolios, credentials, valuation targets or trade plan.
Price/technical details join only on matching date, quality and price. Stale
observations cannot be ranked or marked as new buys. A new buy flag requires an
existing published result from the established recommendation-status RPC.

The security advisor flags authenticated SECURITY DEFINER execution as expected
for this intentional API projection; access checks and allowlisted output are
verified. Private table RLS-with-no-policy notices remain intentional denials.
[Advisor explanation](https://supabase.com/docs/guides/database/database-linter?lint=0029_authenticated_security_definer_function_executable).
No data-rights, publication, execution or email gates were activated.

## Validation

- Database: real snapshot reconciled with source counts, anon denied, raw-table
  read denied, inactive/nonexistent user rejected.
- `node --test engine/tests/live_radar.test.mjs`: filtering/ranking, stale and
  incomplete records, initial-vs-confirmed buying, zero/missing values, schema.
- `node scripts/radar_session_qa.cjs`: isolated browser HTTP fixtures on three
  viewports, controls/details, sector switch, network failure/retry and session
  denial clearing the previous table. It never creates a production account.
- Private browser check uses the current 405-row database projection to verify
  paging, 105 ranked rows, five initial setups and no confirmed buys.
- Full production build, Python/Node suites and multi-viewport website QA.
