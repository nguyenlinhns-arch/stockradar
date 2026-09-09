# ThayLinh PC Control V7.9 — Next Upgrade Sequence

Date: 2026-09-09
Status: implementation order / no new major version

## Principle

Do not add another V7.x label merely for planning. Finish the already-built V7.9 bootstrap trust pipeline first, then use that pipeline for subsequent executable changes.

## Stage 0 — preserve accepted runtime

- Accepted live runtime remains 7.0.0-rc1 until V7.9 gates are complete.
- Do not replace live autostart/rollback pointers while staging is not production-ready.
- Keep V6/last-known-good recovery inventory intact.

## Stage 1 — finish existing V7.9 maintenance gates

This is the immediate blocker and has priority over new executable features.

1. Re-establish/verify staging V7.9 runtime with real watchdog.
2. `pc.maintenance_analyze_patch` on harmless reviewed diff.
3. Local one-use Approval A: `MAINTENANCE_BUILD_TEST`.
4. Fixed AppContainer + Job Object build/test; fresh isolation probe immediately before candidate execution.
5. Produce immutable candidate/package/evidence.
6. Separate local one-use Approval B: `MAINTENANCE_PROMOTE`.
7. Promote through existing `TrustedUpdate.ApplyLocalCandidate` path only.
8. Verify staging health.
9. Run controlled broken-candidate activation and prove automatic rollback.

No remote/self approval, no normal-token sandbox fallback, no parallel updater path.

## Stage 2 — signed online update metadata (`CHECK_ONLY`)

Implement through the proven self-maintenance pipeline.

Files expected to be trust-boundary changes include update service, TrustedUpdate/updater, protocol/status, and tests.

Requirements:
- fixed allow-listed HTTPS release/feed origin;
- ECDSA P-256 signed canonical metadata;
- embedded publisher public key + key id;
- manifest <=100 KB;
- expiry/freshness and monotonic release epoch;
- strict SemVer/channel checks;
- no caller URL/package path;
- bounded status only;
- default local `update_mode=check_only`.

Acceptance: valid signed feed is visible in status, invalid/expired/replayed feed is rejected, and no package is downloaded.

## Stage 3 — online package staging (`STAGE_ONLY`)

Add streaming package download and safe extraction without activation.

Requirements:
- signed expected size + SHA-256;
- <=700 MB hard bound;
- strict redirect/origin policy;
- archive traversal/ADS/reparse/case-collision/compression-bomb defenses;
- release inventory + VERSION/catalog/dependency verification;
- immutable side-by-side staged version;
- no current pointer change;
- power loss during download/extract leaves current runtime bootable.

Default remains `stage_only` until evidence passes.

## Stage 4 — unattended preview activation

Only after existing controlled bad-candidate rollback is PASS.

Requirements:
- `auto_apply_preview` local trusted mode;
- update waits for PC-control idle state;
- no mutation/outcome-unknown/approval/maintenance transaction in flight;
- durable update journal; exactly-once activation recovery;
- reuse existing TrustedUpdate stop/switch/smoke/rollback transaction;
- zero duplicate agent/relay after restart;
- config/device identity/secrets/journal/approvals unchanged.

Acceptance before enabling by default:
- successful update PASS;
- deliberately broken signed preview candidate auto-rolls back PASS;
- 10 restart cycles PASS;
- 10 network disconnect/reconnect cycles PASS.

## Stage 5 — stable auto-update

Enable `auto_apply_stable` only after:
- real Windows reboot/logon/autostart/reconnect PASS on exact candidate;
- required uninterrupted soak PASS;
- preview package is promoted without silent rebuild under the same release identity.

## Stage 6 — Persistent UIA worker

This is the first performance work package after trust/update plumbing is proven.

Design:
- one long-lived private UIA worker child instead of Python + pywinauto + COM startup per request;
- private NDJSON stdio or local authenticated pipe; no network listener;
- worker process owned by existing manager/job/watchdog topology;
- UIA controls are resolved fresh per request; do not retain stale element handles as authority;
- READ request may retry once after a worker crash;
- mutation IPC uncertainty returns `OUTCOME_UNKNOWN` and is never replayed blindly;
- detect Windows session/desktop lock/unlock and rebuild UIA apartment when required;
- one enumeration per normal observation; use targeted AutomationId/ControlType/ClassName first;
- bounded output and request timeout;
- worker cannot expose shell/raw code execution.

Target: warm known-control UIA action/inspect in hundreds or tens of milliseconds locally instead of ~2–3 seconds startup-bound behavior.

## Stage 7 — Fast Capture

After UIA:
- in-memory native Win32 capture/resize/JPEG;
- no normal-path PowerShell/System.Drawing child process;
- window/region first, desktop only when needed;
- bounded resolution/quality/output lifetime;
- retain legacy capture only as staging fallback until regression evidence passes.

## Stage 8 — remote wake optimization

Only after local latency is optimized:
- Realtime/private wake is a hint only;
- command args/authorization stay in existing authenticated poll/claim path;
- fallback polling remains;
- no second side-effect owner and no uncertain mutation replay.

## Release engineering rule

Every executable change after Stage 1 should follow:

`ChatGPT reviewed diff -> analyze exact hash/base -> local Approval A -> isolated build/test -> immutable candidate -> local Approval B -> TrustedUpdate staging/rollback -> evidence`

Once online update reaches stable mode, distribution becomes:

`build/test evidence -> publisher signs canonical manifest -> fixed release origin -> client signature/hash/stage -> idle -> existing TrustedUpdate activation -> health/rollback`

## Stop conditions

Do not progress to the next stage if the current stage lacks real evidence. Do not weaken doctor, sandbox, approval, journal, dedupe, lease, update, or rollback checks merely to advance the sequence.