# ThayLinh PC Control V7.9 — Zalo PC Adapter Contract v1

Date: 2026-09-09
Status: IMPLEMENTATION CONTRACT
Parent: `V7_9_WP_ZALO_OPENCUT_HUB_INTEGRATION_v1.md`
Tracking: #117, #143–#149

## 1. Product target

The primary target is the **Zalo desktop application already installed on the user's Windows PC**.

This adapter is not a Zalo Web adapter and does not depend on Opera as its normal execution path.

Phase 1 purpose:

- read the installed Zalo PC app;
- navigate/control the app;
- read conversation/contact/friend state visible through the app;
- search/open exact conversations;
- inspect existing classification/tag state;
- classify using an already-existing tag and verify the result;
- provide bounded inventory/progress summaries.

Phase 1 explicitly excludes automated outbound messaging.

## 2. Trust and privacy boundary

The adapter MUST NOT:

- read Zalo cookies;
- read authentication tokens;
- read private/internal Zalo databases to bypass the UI;
- automate login, OTP or CAPTCHA;
- modify/patch/replace Zalo binaries;
- enable remote-debugging flags or other invasive app instrumentation;
- upload private Zalo content to an unapproved external service;
- log message bodies in the V7 operation journal.

Zalo PC is third-party software. V7 manages only its own app profile, selector metadata, journal, progress ledger and compatibility state.

## 3. App discovery and profile

The live machine discovery step must determine and pin locally:

- canonical app id: `zalo-pc`;
- exact installed executable identity/hash where permitted;
- product/file version;
- primary process identity;
- primary window identity/class/title pattern;
- installation root fingerprint;
- login/ready state probes;
- Accessibility/UIA characteristics;
- selector profile version/hash.

Do not ship a guessed absolute path before real discovery.

A Zalo version/profile change invalidates mutation capability until read-side regression succeeds on a compatible selector profile.

## 4. Route priority

For each Zalo capability use this order:

1. stable Accessibility/UI Automation semantics from the pinned Zalo PC window;
2. release-hashed Zalo selector/profile logic;
3. targeted visual observation of the Zalo window or exact region;
4. fresh relative pointer/keyboard fallback.

Never use absolute screen-coordinate macros as the primary route.

Never fall back to Zalo Web while the installed Zalo PC app is healthy unless a capability is explicitly declared recovery-only.

## 5. Public semantic surface

The exact MCP/tool packaging may be compacted by V7, but the semantic capability set is:

### Read-only

- `zalo_pc.status`
- `zalo_pc.snapshot`
- `zalo_pc.list_visible_conversations`
- `zalo_pc.search_conversations`
- `zalo_pc.read_selected_conversation`
- `zalo_pc.read_messages`
- `zalo_pc.list_existing_tags`
- `zalo_pc.read_current_tag`
- `zalo_pc.scan_contacts_or_friends`
- `zalo_pc.classification_summary`

### Controlled navigation/mutation

- `zalo_pc.focus`
- `zalo_pc.open_view`
- `zalo_pc.open_conversation`
- `zalo_pc.scroll`
- `zalo_pc.apply_existing_tag`
- `zalo_pc.restore_prior_view` where deterministically supported

The runtime may expose these through a smaller generic `pc.app_read`/`pc.app_execute` surface, but caller input can select only locally catalogued capabilities and validated arguments.

## 6. Hard-denied phase-1 controls

The adapter must reject attempts to invoke:

- message composer Value/Text writes;
- send button;
- Enter-to-send;
- file/media attach or send;
- voice/video call initiation;
- friend request sending;
- automatic reply;
- bulk outreach;
- account/login/OTP/CAPTCHA submission.

Even if UIA exposes these elements, they are not part of the phase-1 capability catalog.

## 7. State schema

A read snapshot should return only task-relevant bounded state, for example:

```json
{
  "schema": "zalo-pc.state.v1",
  "app": {
    "ready": true,
    "profile_version": "...",
    "profile_hash": "...",
    "installed_version": "..."
  },
  "generation": 123,
  "view": "conversations",
  "selection": {
    "conversation_identity_hash": "...",
    "display_name": "...",
    "ambiguous": false
  },
  "visible_conversations": [],
  "current_tag": null,
  "completeness": {
    "scope": "visible_only",
    "unknown": false
  }
}
```

Message text may be returned to ChatGPT when the user asks to read it, but must not be copied into the long-lived operation journal/support report unless explicitly required for the requested user output.

## 8. Observation generation

The Zalo adapter owns a monotonic/bounded `generation`.

Generation is invalidated/incremented on relevant:

- primary window replacement/restart;
- app version/profile change;
- major structure change;
- selected conversation change;
- target list structure/reorder change;
- selector profile reload.

Where reliable, a persistent UIA worker may subscribe to StructureChanged/Selection/Focus/PropertyChanged events to invalidate cached read state quickly. Events are advisory; mutations still require fresh state verification.

Every mutation request contains `expected_generation`. Mismatch => `STALE_STATE`; re-read before any action.

## 9. Conversation identity

Display name is user-visible metadata, not sufficient authority for a mutation.

Use the strongest stable information exposed by the installed app without accessing private internal stores, potentially including:

- app/profile version;
- stable Accessibility element ids when available;
- current list/view generation;
- normalized display name fingerprint;
- bounded list neighborhood/context fingerprint;
- current classification/tag;
- current selection state;
- deterministic search result position only within the same fresh generation.

If identity is ambiguous, return `AMBIGUOUS_TARGET` and do not mutate.

## 10. Reading conversations/messages

Reader strategy:

1. verify app/profile readiness;
2. resolve the requested view/region via UIA/selector;
3. read visible structured elements;
4. preserve visible order;
5. for virtualized lists, scroll incrementally and dedupe by bounded identity/message fingerprint;
6. stop on requested limit/time boundary/repeated frontier;
7. report completeness honestly.

For message rows where UIA exposes sender/time/text/type, return typed fields. If only part is exposed, return unknown fields rather than inventing values.

If a required message region is inaccessible to UIA, request/capture only that Zalo-window region and use visual interpretation as fallback. Whole-desktop screenshots are not the default.

## 11. Contacts/friends inventory and classification

Long scans use a bounded local progress ledger:

```json
{
  "schema": "zalo-pc.scan-progress.v1",
  "generation": 123,
  "total_observed": 0,
  "classified": 0,
  "unclassified": 0,
  "ambiguous": 0,
  "per_tag": {},
  "cursor": null,
  "last_identity_hash": null,
  "last_operation_id": null
}
```

Do not call a partial scan "total friends". Distinguish `TOTAL_OBSERVED` from platform total unless exhaustive traversal has been proven for that Zalo version/view.

Resume requires re-observing the cursor neighborhood; stale/reordered UI triggers a local rescan rather than blind continuation.

## 12. Tag registry and tag mutation

Tag/classification selectors are stored in a signed/release-hashed Zalo profile pack tied to compatible app versions.

Before tag mutation:

1. verify current app/profile compatibility;
2. read current available tag UI/state;
3. confirm exact requested existing tag;
4. resolve exact conversation identity;
5. capture expected generation/current tag;
6. enter operation journal `PREPARED`;
7. perform one tag action;
8. re-read selected conversation/tag;
9. require exact expected tag;
10. journal `COMMITTED` only after verified readback.

Missing/renamed/ambiguous tag => `BLOCKED_TAG_SCHEMA_CHANGED`.

Never auto-create a new Zalo tag in phase 1.

## 13. Operation journal

Zalo mutation journal uses the common V7 app operation state machine:

`PREPARED -> RUNNING -> VERIFYING -> COMMITTED`

Other states:

- `FAILED`
- `OUTCOME_UNKNOWN_RECONCILING`
- `CANCELLED`
- `BLOCKED_USER_ACTIVE`
- `BLOCKED_PROFILE_MISMATCH`
- `STALE_STATE`
- `AMBIGUOUS_TARGET`

Journal content is privacy-minimized:

- operation id;
- app id;
- capability;
- target identity hash;
- expected/result generation;
- old/new tag name or stable id when appropriate;
- route used;
- timestamps;
- result/reason code.

Do not store message text, contact details beyond what is necessary for the user-facing result, cookies, tokens or screenshots in the journal.

## 14. Physical-user and concurrency safety

Read-only non-intrusive observation may proceed when safe without stealing focus.

Any operation that focuses/navigates/mutates Zalo PC is blocked when:

- V7 says `USER_ACTIVE_RETRY_LATER`;
- remote mutation lease is unhealthy;
- global pause/emergency stop is active;
- another Zalo mutation is in flight;
- an unresolved Zalo `OUTCOME_UNKNOWN` exists;
- app profile is mismatched;
- self-update/maintenance activation is in a conflicting phase.

One app-specific mutation lane prevents concurrent UI races.

## 15. Performance design

The initial performance strategy is a persistent UIA worker rather than starting Python/pywinauto/COM for every call.

Requirements:

- one private out-of-process worker;
- strict NDJSON framing;
- fixed trusted worker/runtime hash;
- stable COM apartment/thread;
- bounded queue;
- cancellation and watchdog;
- fresh element resolution per command;
- no long-lived UI element object assumptions;
- one safe retry only for read-side transient failures;
- mutation IPC uncertainty => `OUTCOME_UNKNOWN`, never automatic replay.

Measure cold/warm P50/P95 for status, list, search/open and read-message operations on the real Zalo version before promotion.

## 16. Signed profile updates

Because Zalo PC may update independently of V7, selector/profile metadata should be updateable as a small signed app-profile pack.

Profile pack may contain only data/selector/compatibility metadata. It cannot contain arbitrary executable code or new permissions.

Activation flow:

1. detect installed Zalo version/profile mismatch;
2. check trusted profile feed;
3. download/stage signed/hash-pinned profile;
4. schema + compatibility validate;
5. run read-only Zalo regression;
6. activate profile only if regression passes;
7. keep previous profile for rollback;
8. mutation remains blocked until compatible profile is active.

Adapter code changes still use V7 self-maintenance/TrustedUpdate, not profile hot-swap.

## 17. Acceptance tests

### Discovery
- installed Zalo PC discovered without guessed absolute path;
- exact process/window/profile pinned;
- no second unrelated process accepted;
- login/not-ready state reported without credentials.

### Read
- list visible conversations;
- exact search/open;
- read selected conversation visible messages;
- virtualized scroll does not duplicate already observed rows;
- partial scan reports partial completeness;
- no message bodies leak into support/journal logs.

### Safety
- duplicate display-name targets => no mutation;
- app/profile version mismatch => no mutation;
- USER_ACTIVE => no focus/navigation/tag mutation;
- composer/send/attach/call actions are not in allowed capability catalog;
- UIA/worker disconnect during mutation => outcome unknown/no blind retry.

### Classification
- existing exact tag discovered;
- one reversible test conversation selected with exact identity;
- tag applied once;
- post-read exact tag verified;
- journal receipt matches result generation;
- stale generation before apply => blocked and reread required.

### Performance
- warm persistent UIA measurements recorded;
- lower latency does not increase stale-state/unknown-outcome rate.

### Compatibility update
- changed app version invalidates mutation profile;
- signed matching profile stages and read-only regression passes before activation;
- bad profile rejected/rolled back.
