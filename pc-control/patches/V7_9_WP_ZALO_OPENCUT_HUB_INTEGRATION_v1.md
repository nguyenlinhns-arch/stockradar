# ThayLinh PC Control V7.9 — Zalo PC + OpenCut + ThayLinh Hub Integration v1

Date: 2026-09-09
Status: DESIGN / IMPLEMENTATION SOURCE OF TRUTH
Tracking: #114, blocker #115

## 0. Scope lock

This V7.9 integration wave is intentionally limited to three targets:

1. **Zalo PC installed on Windows** — primary Zalo target. Read and control the installed desktop app for navigation, search, conversation reading, contacts/friends inventory, existing-tag classification and verified status. Zalo Web/Opera is recovery-only.
2. **OpenCut Classic** — primary video editor target. Use the existing semantic bridge where possible, with UIA/visual fallback only for gaps.
3. **ThayLinh Automation Hub** — reuse its lifecycle, reliability, self-update, transaction, app-management and observability patterns as shared infrastructure; do not merge Hub business workflows into PC Control.

Business data stays outside PC Control. V7.9 is an execution/control plane, not a data warehouse.

## 1. Non-negotiable authority model

- V7 local installed policy remains the authorization authority.
- App manifests/profiles identify an app/capability but never grant permission.
- Exact approved executable identity/hash/arguments, USER_ACTIVE/session guard, lease ownership, ApprovalStore, journal/dedupe, pause/emergency stop and TrustedUpdate rollback remain authoritative.
- No arbitrary shell, executable path, argv, URL, JavaScript, PowerShell or script execution is introduced.
- A transport ACK is never equivalent to a successful side effect. Mutations require post-read verification.
- If a side effect outcome is uncertain, return `OUTCOME_UNKNOWN_RECONCILING`; do not blindly retry.

## 2. Common ManagedApp lifecycle contract

Promote the useful ThayLinh Hub lifecycle model into V7.9 as a generic local contract.

Recommended data fields:

```json
{
  "schema": "thaylinh.managed-app.v1",
  "app_id": "zalo-pc",
  "display_name": "Zalo PC",
  "profile_version": "1",
  "root_fingerprint": "...",
  "adapter": {"kind": "zalo-pc", "version": "1"},
  "declared_capabilities": [],
  "managed_files": [],
  "required_paths": [],
  "preserve_paths": [],
  "baseline_hashes": {},
  "process_identity": {},
  "window_identity": {},
  "health_probes": [],
  "selector_profile_hash": null,
  "mutation_policy": "local-policy-owned",
  "update_policy": "trusted-only"
}
```

Hard rules:

- path fields are relative to an already approved narrow root where applicable;
- reject `..`, absolute paths from caller input, symlink/reparse escapes and unknown privileged keys;
- preserve user data/config/session/token/media/project outputs;
- app lifecycle write/upgrade uses expected SHA, per-app lock, backup, validate/test/health and rollback;
- interrupted upgrade becomes `recovery_required` and blocks further app writes until resolved;
- manifest/fingerprint is identification metadata only.

## 3. Common app-operation journal

Use one app mutation state model across Zalo PC, OpenCut and managed-app upgrades:

`PREPARED -> RUNNING -> VERIFYING -> COMMITTED`

Explicit non-success states:

- `FAILED`
- `OUTCOME_UNKNOWN_RECONCILING`
- `ROLLBACK_REQUIRED`
- `ROLLED_BACK`
- `CANCELLED`
- `BLOCKED_USER_ACTIVE`
- `BLOCKED_PROFILE_MISMATCH`
- `BLOCKED_RECOVERY_REQUIRED`

Persist only privacy-bounded evidence:

- operation/idempotency id;
- app id + capability;
- expected revision/identity/profile hash;
- pre/post state hashes or bounded typed evidence;
- started/completed timestamps;
- adapter route used;
- bounded error/reason code;
- rollback/checkpoint id where supported.

Do not log Zalo message bodies or tokens. Do not log raw private update URLs/secrets. OpenCut logs should prefer project/revision/media hashes rather than media content.

## 4. Capability router

Fixed priority for every capability:

1. native/app semantic connector;
2. app-local release-hashed selector/profile;
3. targeted UI Automation/Accessibility;
4. targeted visual observation of the app/window/region;
5. fresh relative pointer/keyboard input as last fallback.

Rules:

- fallback never broadens permission or changes intent;
- no whole-desktop observation when app/window-targeted observation is enough;
- no stale coordinate macros;
- unsupported capability returns explicit unsupported/profile-mismatch state instead of improvising;
- mutation is blocked while USER_ACTIVE, global pause/emergency stop, unhealthy lease, update promotion, unresolved unknown outcome or app transaction lock is active.

## 5. Zalo PC — primary desktop adapter

### 5.1 Target

Primary target is the **installed Windows Zalo desktop application**. Do not treat Opera/Zalo Web as the normal route.

At first live discovery on the PC:

1. discover installed Zalo app using bounded known application roots/Windows installed-app metadata;
2. pin exact executable identity/hash and installed version locally;
3. launch/focus the exact approved app only;
4. enumerate process/window identities;
5. capture a bounded UIA/Accessibility tree of the Zalo window;
6. create a release-hashed selector/profile for the observed version;
7. run read-only selector regression before any mutation capability is enabled.

Do not hard-code a path such as `Zalo.exe` before local discovery proves the actual installation identity.

### 5.2 Phase-1 allowed controls

Allowed:

- `zalo_pc.status`
- launch/focus/recover Zalo PC
- identify login/ready/not-ready state without automating credentials
- navigate primary views/tabs
- open Contacts/Friends/conversation lists
- search exact friend/conversation
- open an exact conversation
- scroll/read visible conversation context/messages
- read current classification/tag state
- list/verify existing tags
- apply one existing tag/classification
- verify tag after mutation
- scan/count observed conversations/friends and per-tag classification progress

Hard deny in phase 1:

- auto-reply;
- typing into message composer;
- pressing Send/Enter-to-send;
- sending files/media;
- bulk outreach;
- automated login/OTP/CAPTCHA;
- reading Zalo cookies/tokens/private databases;
- bypassing Zalo platform protections.

### 5.3 Zalo PC reader

Read pipeline:

1. verify Zalo PC app profile/version;
2. inspect app-local Accessibility/UIA elements;
3. resolve the required list/conversation region fresh on each operation;
4. if a virtualized list is used, scan incrementally using a generation/cursor and dedupe conversation identity hashes;
5. read only the visible/required message range for the task;
6. if UIA cannot expose a required visual region, use targeted window-region vision fallback;
7. return completeness state explicitly.

Inventory result must distinguish:

- `TOTAL_OBSERVED`
- `CLASSIFIED`
- `UNCLASSIFIED`
- `AMBIGUOUS`
- `UNKNOWN_NOT_SCANNED`
- scan generation/cursor

A partial scan must never be reported as the total number of Zalo friends/conversations.

### 5.4 Conversation identity

Display name alone is not sufficient for a write.

Construct a privacy-minimized identity from stable attributes exposed by the installed app where available:

- Zalo PC profile/version;
- accessible element/automation identifiers;
- list generation and bounded position/context;
- normalized display-name fingerprint;
- current tag/classification;
- current selection state;
- bounded surrounding UI fingerprint.

If multiple candidates remain plausible, mark ambiguous and do not mutate.

### 5.5 Existing-tag classification

Tags are controlled by a local, release-hashed Zalo-PC tag/selector registry. Before a batch:

1. verify current Zalo PC version/profile;
2. read currently available/visible tag set;
3. map exact normalized names/accessible identifiers;
4. confirm the requested tag exists;
5. preflight exact target identity + current tag;
6. perform one semantic classification mutation;
7. re-read exact target and exact expected tag;
8. commit the journal only after verification.

Example existing tag such as `Đăng ký cũ` may be used only after the installed Zalo PC instance verifies it exists. Never create or guess a near tag automatically.

### 5.6 Classification progress ledger

Persist bounded progress outside Zalo private storage:

- total observed;
- classified;
- per-tag counts;
- unclassified;
- ambiguous/blocked;
- scan cursor/generation;
- last verified identity hash;
- last operation id.

No message bodies are stored in this progress ledger. Resume requires re-observation of the local neighborhood before the next mutation.

### 5.7 Performance

Persistent UIA worker is the preferred fallback acceleration layer:

- one private out-of-process worker;
- strict NDJSON stdio;
- fixed bundled Python/worker hash;
- stable COM apartment/thread;
- fresh element resolution rather than stale object reuse;
- one safe retry for read-only transient failures;
- mutation IPC uncertainty => `OUTCOME_UNKNOWN`, no replay;
- host owns USER_ACTIVE/lease/pause/cancel gates.

The goal is to avoid the repeated 2–3 second UIA startup overhead while not turning UIA into a generic macro engine.

## 6. OpenCut Classic — semantic editor adapter

### 6.1 Correctness first

Before adding speed features, complete the current Classic regression:

- bridge health/state;
- project create/save/reload;
- bridge-owned Date revival at all OpenCut storage boundaries;
- checkpoint/mutate/restore;
- deterministic timeline mutation smoke;
- exact project id + expected revision transaction;
- rollback on invalid later step;
- uncertain disconnect => outcome unknown/no blind replay;
- export to new file + ffprobe/decode validation.

Do not patch upstream storage globally without a new failing reproduction.

### 6.2 EditSpec / batch / delta

After correctness passes, V7 owns an `EditSpec` compiler above the existing OpenCut bridge.

Required features:

- project/base revision fence;
- transaction/idempotency id;
- preflight;
- checkpoint;
- batch semantic operations;
- post-state verification;
- rollback;
- delta edits rather than rebuild-from-zero;
- replace-clip-keep-duration;
- 9:16 reframe;
- text role/style tokens;
- export profile + QA.

No raw arbitrary JS/script execution.

### 6.3 Text roles

Initial roles:

- `HOOK`
- `KEYWORD`
- `LOCATION`
- `STORY`
- `LOWER_THIRD`
- `ENDING`

Current project defaults where locally available:

- Montserrat SemiBold/Black;
- lead white;
- keyword `#F4C70F`;
- negative-space placement;
- mobile safe area;
- do not cover faces/bodies;
- short fade/vertical-slide/soft-pop primitives;
- content/style/motion stored separately.

### 6.4 Proxy/cache and review

After correctness:

- content-addressed proxy/cache from source fingerprint + proxy version;
- cache metadata/keyframes/thumbnails/waveforms;
- preview may use proxy/half/quarter quality;
- final export always resolves original media; proxy-in-final => hard fail;
- compact review API returns timeline summary + selected chapter/storyboard frames/text placements;
- native playback remains final visual/timing review.

### 6.5 Export QC

Default social-high target unless project explicitly overrides:

- 1080x1920;
- CFR, normally 30 fps;
- H.264;
- yuv420p;
- Rec.709 SDR;
- AAC 48 kHz;
- source-aware HDR handling, not retagging.

After export verify actual file with ffprobe/decode: resolution/FPS/codec/pixel format/duration/audio/color metadata and timeline duration tolerance. Hardware encode is an optimization only; QC remains identical.

## 7. ThayLinh Hub patterns reused

Reuse as shared V7 infrastructure:

- managed app discovery/identity/lifecycle concepts;
- narrow app root;
- managedFiles/requiredPaths/preserve/process/baseline;
- source read returning SHA before edit;
- per-app lock;
- backup/test/health/rollback;
- recovery_required after interrupted/unknown upgrade;
- signed/hashed update concepts;
- supervisor/single-instance/health patterns;
- emergency stop/pause semantics;
- durable outbox/journal style: commit intent before external side effect;
- unknown outcome reconciliation before retry;
- privacy-minimized support reports.

Do **not** copy into PC Control:

- social publishing business workflows;
- recruitment data;
- Messenger content;
- content libraries;
- Hub SQLite business tables;
- any app-specific permission that would weaken V7.

## 8. Acceptance order

No promotion may skip this order:

1. **#115 Self-maintenance C2/C3**: Approval A -> isolated build/test -> immutable candidate -> Approval B -> TrustedUpdate promotion -> forced bad candidate rollback PASS.
2. **ManagedApp lifecycle core**: identity must not grant authority; preserve/backup/recovery tests PASS.
3. **Zalo PC discovery/read-only**: exact app profile + UIA/selector read regression + inventory completeness semantics PASS.
4. **OpenCut Classic correctness**: Date/storage + transaction + checkpoint/rollback + export QA PASS.
5. **Zalo PC controlled classification**: exact identity, existing tag, one mutation, post-read verification, ambiguity fail-closed PASS.
6. **Persistent UIA performance**: faster warm reads without changing mutation safety PASS.
7. **OpenCut EditSpec/text/proxy/review/export optimizations**.
8. **Three-app integration matrix #120** and regression on normal ChatGPT path.

Evidence must state one of: `STATIC PASS`, `STAGING PASS`, `LIVE PASS`. Design/spec presence never counts as runtime success.

## 9. Update/release integration

All components introduced here must be delivered through the V7.9 trusted maintenance/update boundary once #115 is proven. The online updater remains gated as designed:

`CHECK_ONLY -> STAGE_ONLY -> AUTO_APPLY_PREVIEW -> AUTO_APPLY_STABLE`.

App/profile updates must be signed/hashed and compatibility-gated. A Zalo/OpenCut app version change that invalidates selectors blocks mutation until a new profile passes read-only regression.
