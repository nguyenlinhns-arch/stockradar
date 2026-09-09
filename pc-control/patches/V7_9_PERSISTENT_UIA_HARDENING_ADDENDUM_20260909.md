# V7.9 Persistent UIA — hardening addendum

Date: 2026-09-09
Status: review/design addendum
Base: `V7_9_PERSISTENT_UIA_FAST_OBSERVE_SPEC.md` in the project source of truth

This addendum does not change rollout order: implement only after the V7.9 self-maintenance build/promote/rollback gates are proven. It tightens lifecycle, framing, COM/session handling and mutation uncertainty.

## 1. Spawn integrity

Before spawning the persistent UIA worker, the host verifies that all executable inputs are the exact installed release inputs:

- bundled `pythonw.exe`/Python runtime identity;
- worker script/module hash;
- relevant immutable adapter module hash where the current release inventory supports it.

Hashes/paths must resolve under the active immutable V7 version root and match the release inventory. No config/tool/caller may supply another interpreter, worker script or module search path.

Use an explicit minimal environment. Do not inherit arbitrary `PYTHONPATH`, `PYTHONSTARTUP`, user-site packages or shell profile state. Prefer bundled isolated Python semantics and disable user-site imports.

## 2. Protocol framing

NDJSON is acceptable only if stdout is protocol-exclusive. Imported libraries must never be allowed to write ordinary diagnostics to the protocol stream.

Preferred implementation:

- save the dedicated binary protocol stream at worker bootstrap;
- route Python/logging/library diagnostics to bounded stderr;
- use a 4-byte unsigned little-endian length prefix followed by exact UTF-8 JSON payload OR enforce exact one-line JSON with a hard line-length bound and no library stdout;
- reject zero/oversize frames before allocation;
- request <=128 KiB, response <=2 MiB;
- protocol version and request id mandatory;
- response request id + worker generation must match the active request;
- no unsolicited action/result messages.

If length-prefix framing would make the first patch materially larger, NDJSON may ship first but must include tests where accidental stdout noise causes a fail-closed worker recycle, never a JSON desynchronization that could mis-associate a mutation result.

## 3. COM apartment/thread invariant

Initialize pywinauto/UIAutomationClient/UFO and execute all ordinary UIA operations on the same dedicated worker thread/apartment unless a component is explicitly documented thread-safe.

Do not use a generic thread pool to enforce per-request deadlines; doing so can move COM proxies across apartments and create intermittent failures.

Deadline enforcement model:

- parent owns request deadline;
- worker cooperatively checks deadline between bounded stages when practical;
- if a READ hangs beyond hard deadline, parent terminates/recycles the worker and may retry that READ once;
- if a MUTATION may have crossed its side-effect boundary, termination/IPC loss returns `OUTCOME_UNKNOWN` and is never automatically replayed.

## 4. Explicit mutation phase

Worker internally tracks a request phase for diagnostics/uncertainty classification:

`RECEIVED -> RESOLVING -> PRE_SIDE_EFFECT -> SIDE_EFFECT_STARTED -> VERIFYING -> COMPLETE`

The worker may report phase in bounded internal diagnostics. This does not authorize retries by itself.

Rules:
- crash/IPC loss known before `SIDE_EFFECT_STARTED`: mutation may be dispatched once only when the host has positive evidence the previous worker died before side effect;
- any uncertainty at/after `SIDE_EFFECT_STARTED`: `OUTCOME_UNKNOWN`;
- host command journal remains authority for replay/dedupe; worker does not create a second mutation ledger.

## 5. Host-authoritative guard

Keep the current `/gui-input-check` behavior initially if replacing it would broaden the patch. The long-lived worker must not cache ALLOW across mutations.

Future preferred optimization is a private parent-mediated guard challenge over the owned IPC, not a public listener:

`worker GUARD_REQUEST(request_id,target_digest,action) -> host GUARD_DECISION(allow/deny,guard_epoch,short_expiry)`

Any such decision is single-request, short-lived and bound to worker generation + target digest. Pause/user-active/cancel/lease/update state remain host-authoritative.

Do not use a reusable bearer token that lets the worker authorize its own later mutations.

## 6. Session/desktop lifecycle

UIA state can become invalid across Windows lock/unlock, fast user switching, RDP attach/detach, logoff/logon and desktop changes.

Parent tracks the interactive session/desktop identity used by the worker. On a relevant transition:

- block new GUI mutations;
- mark current worker generation stale;
- if no mutation side effect is uncertain, terminate worker;
- lazily create a fresh worker only after an interactive usable desktop is available;
- first request after recreation reinitializes COM/UIA and resolves all elements fresh.

Never carry AutomationElement/control handles across session/desktop changes.

## 7. Worker resource ceilings

Track by generation:

- PID/process start identity;
- working set/private bytes where available;
- request count;
- age;
- consecutive protocol/COM failures;
- last successful request time.

Use bounded recycle thresholds with hysteresis. A threshold schedules recycle when idle; it does not interrupt an in-flight mutation merely to satisfy age/request count.

A crash loop trips a circuit breaker and falls back to the existing per-call worker/debug path for READs only where policy permits, while GUI mutation remains fail-closed until health is restored.

## 8. Selector/result safety

Persistent lifetime must not introduce ambient authority:

- resolve HWND/control fresh per request;
- no live AutomationElement retained as a cross-request cache;
- selector parser remains strict and bounded;
- ambiguous selector remains failure;
- result text/tree remains bounded exactly as current semantic output policy requires;
- no clipboard contents, browser secrets, password values or hidden control values are added merely because the worker is persistent.

## 9. Fast observe consistency

When removing duplicate full UI enumeration:

- issue observation token only after all requested components were collected;
- bind token to target HWND/process identity, rect, foreground state when relevant, worker generation, and capture/inspect timestamps;
- recheck cheap Win32 identity/geometry after capture/inspect;
- if target identity changes during observation, fail/re-observe instead of creating a mixed-state token;
- a worker generation change invalidates any token that relied on that worker's UIA snapshot for a subsequent mutation.

Do not require a second full UI tree enumeration merely to start the token TTL.

## 10. Acceptance additions

In addition to the base spec:

1. Spawn refuses a modified worker script/interpreter hash.
2. User `PYTHONPATH`/site customization cannot inject worker code.
3. Accidental stdout noise cannot become a valid/mis-associated response.
4. Oversize frame is rejected before unbounded allocation.
5. Worker stays on intended COM execution thread across 1000 READs.
6. Lock -> unlock recreates worker and next READ succeeds.
7. RDP/session transition does not reuse old UIA handles.
8. READ hard hang -> worker killed -> one safe retry succeeds.
9. Mutation IPC failure after side-effect boundary -> `OUTCOME_UNKNOWN`, zero replay.
10. Worker memory/request/age recycle happens only when idle.
11. Persistent worker crash loop does not cause an infinite restart storm.
12. Observation token from old worker generation cannot authorize a later GUI mutation.
13. Warm performance target remains >=5x improvement over the measured per-process baseline.
