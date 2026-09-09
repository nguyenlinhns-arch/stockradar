# ThayLinh PC Control V7.9 — Online Auto-Update Contract v2

Date: 2026-09-09
Target: V7.9.x preview -> stable
Scope: extend the existing TrustedUpdate + manager/watchdog architecture. Do not create a second agent, relay, manager, promotion path, or rollback engine.

## Current-state constraint

V7.9 is currently a staging candidate, not the accepted production runtime. Auto-update therefore rolls out in four gates and MUST NOT jump directly to unattended activation:

1. `CHECK_ONLY` — fetch and validate signed metadata; no package download.
2. `STAGE_ONLY` — download, verify, and stage package; do not switch `current.json`.
3. `AUTO_APPLY_PREVIEW` — unattended activation only after the existing V7.9 maintenance/promote/rollback gates and controlled bad-candidate rollback have passed.
4. `AUTO_APPLY_STABLE` — only after preview acceptance plus restart/network/reboot/soak evidence on the exact candidate.

The currently accepted live runtime remains last-known-good until those gates pass.

## Goals

- Check a fixed trusted online feed automatically after the manager reaches HEALTHY and periodically thereafter.
- Preserve `preview` and `stable` channels through the existing `update_channel` setting.
- Reuse the existing TrustedUpdate activation/smoke/rollback transaction.
- Keep the local hash-pinned feed as offline/recovery fallback.
- Never overwrite persistent identity, config, secrets, user files, logs, approvals, recovery state, or rollback inventory.
- Make network/repository failure non-fatal to normal PC-control operation.

## Hard safety rules

- No caller-supplied update URL, package URL, executable path, source root, signing key, certificate, or release asset path.
- No generic shell/terminal/raw command is introduced for update or release handling.
- No package executes before metadata signature, size, SHA-256, archive safety, release inventory, and version checks pass.
- No update is replayed automatically after an uncertain activation outcome; resume from the durable update journal instead.
- Never permanently disable watchdog protection for an update.
- Never delete last-known-good until a newer release is committed and retention rules are satisfied.

## Trust model — two independent requirements

HTTPS + repository allow-list alone is not sufficient because a compromised repository could replace both manifest and package/hash.

Every online release therefore requires BOTH:

1. **Trusted origin** — HTTPS, fixed allow-listed GitHub repository/release origin compiled into the client. Final redirect host/origin must remain allow-listed.
2. **Publisher signature** — canonical release metadata must verify against a P-256 ECDSA public key embedded in the installed updater/trust library.

SHA-256 remains mandatory for exact package integrity, but the SHA value itself is trusted only after the signed metadata verifies.

The private signing key is NEVER stored in the repository, update package, installed PC-control data directory, ChatGPT-visible files, or remotely callable configuration. Publishing may be automated; release signing remains a separate publisher trust action.

Key rotation requires a release signed by the currently trusted key that authorizes the next public key and activation epoch. Emergency key removal is handled only through the existing local recovery/bootstrap path.

## Canonical signed metadata

The feed is an envelope. `signed` is canonical JSON and `signature` authenticates its exact UTF-8 canonical byte representation.

```json
{
  "schema": "thaylinh.pc.update-feed.v2",
  "key_id": "publisher-p256-2026-01",
  "signed": {
    "channel": "preview",
    "version": "7.9.0-rc2",
    "release_id": "v7.9.0-rc2",
    "release_epoch": 2,
    "published_at": "2026-09-09T12:00:00Z",
    "expires_at": "2026-09-16T12:00:00Z",
    "min_manager_version": "7.9.0-rc1",
    "min_safe_version": "7.9.0-rc1",
    "package": {
      "asset": "ThayLinh-PC-Control-7.9.0-rc2.zip",
      "size": 12345678,
      "sha256": "<64 lowercase hex>"
    },
    "health": {
      "timeout_seconds": 90,
      "required_agent_count": 1,
      "required_relay_count": 1
    }
  },
  "signature": "<base64 ECDSA P-256 SHA-256 signature>"
}
```

Canonicalization rules are fixed by implementation and tests: UTF-8, deterministic property order, no insignificant whitespace, numeric values encoded invariantly, no duplicate JSON property names. Unknown top-level trust fields fail closed until explicitly supported by the installed schema version.

## Metadata bounds and freshness

- Manifest response: `1..100000` bytes before JSON parsing.
- Package: `1..700000000` bytes from signed metadata and enforced while streaming.
- Metadata signature must verify before trusting channel/version/package hash.
- `published_at` cannot be implausibly far in the future relative to the local trusted clock policy.
- `expires_at` is mandatory and bounded; expired metadata is rejected.
- Persist highest committed `release_epoch` per channel. Automatic update rejects lower epochs even when a version string appears newer.
- A release ID may map to only one signed package hash. Conflicting metadata for an already observed release ID is a security error, not an update.

## Version and anti-rollback policy

- Strict SemVer-compatible parsing; malformed versions fail closed.
- Automatic path accepts only a version newer than the installed/committed version for that channel.
- `release_epoch` must not decrease.
- `min_safe_version` may prevent activation of a known-unsafe older candidate but may never silently delete rollback evidence.
- Downgrade is forbidden in automatic mode.
- Recovery downgrade to last-known-good is allowed only as rollback/recovery, not as a normal feed update.
- Idempotency key: `channel + release_id + package.sha256 + release_epoch`.

## Fixed package resolution

The signed manifest carries an asset identifier, not an arbitrary URL. The client constructs the download location from its compiled allow-listed owner/repository/release origin plus `release_id` and `asset` after validating both against strict character/length rules.

Redirects are disabled where practical. If the platform requires a release-asset redirect, every hop and final origin must match the explicit allow-list; credentials are never forwarded to an untrusted host.

## Check cadence

- First check only after manager/watchdog reach HEALTHY.
- Default periodic check: every 6 hours.
- Per-device jitter: 0..10 minutes.
- Exponential backoff for transient network errors.
- Offline/GitHub/feed failure does not degrade local control health.
- Reconnect does not trigger an unbounded immediate check loop.

## Busy/idle activation gate

Automatic package verification may run while the system is otherwise healthy, but activation waits until the PC-control runtime is idle:

- no mutation command in flight;
- no command with outcome UNKNOWN;
- no maintenance promotion transaction in flight;
- no local approval transaction being consumed;
- no active GUI atomic-input section;
- watchdog and journal healthy;
- update journal has no unresolved transaction.

If busy, keep the package staged and retry activation later. Never interrupt an active user-visible mutation merely to update.

## State machine

`IDLE -> CHECKING -> AVAILABLE -> DOWNLOADING -> VERIFIED -> STAGED -> WAITING_FOR_IDLE -> INSTALLING -> HEALTH_CHECK -> COMMITTED`

Failure/recovery:

- metadata/network failure -> `IDLE` with bounded diagnostic;
- verification failure -> `REJECTED` and package deleted from staging;
- install/health failure -> `ROLLBACK -> HEALTH_CHECK -> ROLLED_BACK`;
- rollback health failure -> existing SAFE MODE + preserved diagnostics;
- process/power loss -> launcher reads durable update journal and deterministically resumes health-check or rollback; it never blindly starts a second activation transaction.

Every state transition is atomically journaled before its external side effect when ordering permits.

## Side-by-side installation

Prefer immutable version directories:

```text
%LOCALAPPDATA%\ThayLinhPCControl\
  current.json
  versions\
    7.9.0-rc1\
    7.9.0-rc2\
  staging\
  data\
    update-journal.json
    update-security-state.json
```

Persistent `data` is outside release payloads. Release packages cannot include paths targeting `data`, `versions` siblings, startup folders, Windows/system paths, user documents, browser profiles, or Drive folders.

## Safe archive extraction

Before extracting any entry, reject:

- absolute paths, drive-qualified paths, UNC/device paths;
- `..`, empty/dot components, alternate data streams, NUL/control characters;
- symlink/hardlink/reparse-point payloads or extraction through an existing reparse point;
- duplicate normalized paths;
- case-collision paths on Windows;
- files outside the candidate version root after canonical resolution;
- per-entry or total extracted-size overflow / compression bombs;
- unexpected executable inventory not declared by release inventory.

Extract to a new empty staging/version directory only.

## Release inventory gate

After extraction but before activation:

- validate `VERSION.json` / release metadata version equals signed version;
- validate release inventory/per-file hashes through existing RELEASE validation;
- validate catalog hash and dependency locks where applicable;
- verify expected updater/manager/agent entrypoints exist;
- prohibit files in protected persistent-data locations;
- record exact candidate inventory hash in the update journal.

## Activation transaction

1. Confirm selected rollout mode permits activation (`AUTO_APPLY_PREVIEW`/`STABLE`).
2. Confirm HEALTHY + idle gate + no unresolved update transaction.
3. Re-verify signed metadata and staged package/inventory hashes.
4. Record transaction, previous version, staged version, signed release identity and hashes atomically.
5. Enter existing watchdog update/maintenance phase.
6. Atomically switch version pointer using the existing TrustedUpdate mechanism.
7. Restart through existing launcher/manager path.
8. Run existing smoke/health plus updater-specific gates.
9. Commit current/rollback/last-known-good only on PASS.
10. On any failure or timeout, restore previous pointer/data state using existing TrustedUpdate rollback.

Do not create a second swap/rollback implementation.

## Health gate

A process launch is not acceptance. Required before commit:

- manager/watchdog healthy;
- exactly one intended agent and relay/gateway instance where applicable;
- local semantic/MCP health responds;
- reported version/catalog identity equals staged release;
- no immediate restart/crash loop;
- updater/install/rollback inventories are readable;
- protected config/device identity/secrets remain unchanged;
- existing read-only smoke path succeeds;
- for trust-boundary updater releases, a bounded post-start grace window passes without watchdog degradation.

Default health timeout: 90 seconds, bounded by implementation.

## Protected persistent data

Packages and migrations must not overwrite/delete:

- config.json and local policy;
- machine/device identity;
- DPAPI secrets/tokens/credentials;
- local approval keys/receipts;
- command journal/dedupe/lease state;
- logs/diagnostics;
- safe-mode state;
- update journal/security state;
- rollback/last-known-good metadata;
- maintenance trust/source configuration;
- user files.

Any persistent-data migration is explicit, versioned, backed up, hash/evidence recorded, and reversible before candidate commit.

## Rollout modes

`update_mode` is a local trusted setting, not remotely supplied:

- `disabled`
- `check_only`
- `stage_only`
- `auto_apply_preview`
- `auto_apply_stable`

The initial V7.9 online-update bootstrap MUST default to `check_only`. Promotion to a more permissive mode is allowed only after acceptance evidence for the preceding mode.

## Release publishing separation

Build and publishing may be automated, but trust roles remain distinct:

1. Build system creates deterministic package + inventory + unsigned canonical metadata.
2. Tests/acceptance produce evidence.
3. Publisher signs exact canonical metadata with the offline/protected P-256 private key.
4. Signed envelope + matching release asset are published to the fixed repository origin.
5. Installed clients independently verify signature/hash/version/freshness before any stage/apply action.

No CI job may mint a trusted signature merely because unreviewed repository source changed unless the signing environment has its own protected approval policy.

## Status surface

Expose only bounded non-secret state:

```json
{
  "currentVersion": "7.9.0-rc1",
  "updateChannel": "preview",
  "updateMode": "check_only",
  "updateState": "idle",
  "latestVersion": "7.9.0-rc2",
  "metadataSignature": "verified",
  "lastCheck": "2026-09-09T12:00:00Z",
  "lastUpdate": null,
  "rollbackAvailable": true
}
```

Do not disclose source paths, staging paths, tokens, signing material, credentials, package temporary URLs, or local approval contents.

## Acceptance ladder

### CHECK_ONLY
1. Valid signed metadata -> reports available version; no package downloaded.
2. Invalid signature/key/schema -> rejected.
3. Expired/replayed/lower-epoch metadata -> rejected.
4. Offline/HTTP failure -> PC Control remains healthy.
5. Arbitrary/cross-origin URL cannot be injected through public tools/config payloads.

### STAGE_ONLY
6. Correct package downloads and exact size/SHA verifies.
7. Oversize, wrong SHA, path traversal, reparse, ADS, case collision, zip bomb -> reject; never execute.
8. Extracted inventory/release/version mismatch -> reject.
9. Staging does not change current pointer or running process.
10. Power loss during download/extract leaves old runtime bootable.

### AUTO_APPLY_PREVIEW
11. Busy mutation -> package waits; no interruption.
12. Successful candidate -> existing TrustedUpdate smoke commits it.
13. Deliberately broken candidate -> automatic rollback PASS.
14. Lost response/power during activation -> durable journal resolves exactly once.
15. Config/device identity/secrets/approvals/journal unchanged across successful update.
16. Zero duplicate agent/relay after update.
17. Ten restart cycles + ten network cycles pass.

### AUTO_APPLY_STABLE
18. Real Windows reboot/logon autostart/reconnect PASS on the exact candidate.
19. Required uninterrupted soak PASS.
20. Preview-to-stable promotion uses the exact previously verified package/signature or a separately signed stable release identity; no silent rebuild under the same release ID.

## Integration rule

This remains a V7.9 enhancement. The existing manager/watchdog and TrustedUpdate own orchestration/activation/rollback. A tiny bootstrap/launcher helper may switch files that a running process cannot replace, but it must consume only the pre-verified local update journal and may not fetch network data or accept caller URLs.