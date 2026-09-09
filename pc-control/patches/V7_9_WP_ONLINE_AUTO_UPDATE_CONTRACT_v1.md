# ThayLinh PC Control V7.9 — Online Auto-Update Contract v1

Date: 2026-09-09
Target: V7.9.0-rc2 / V7.9.x preview
Scope: Extend the existing TrustedUpdate + manager/watchdog architecture. Do not create a second agent, relay, manager, or watchdog.

## Goals

- Automatically check a trusted online feed at startup and every 6 hours while the manager is healthy.
- Support `preview` and `stable` channels; preserve the existing `update_channel` setting.
- Download only from a fixed, application-owned GitHub feed/release origin.
- Stage, verify, install, restart, health-check, and automatically roll back on failure.
- Keep the existing local hash-pinned update feed as an offline/recovery fallback.
- Never overwrite persistent identity, configuration, secrets, user files, logs, or recovery state.

## Non-goals / hard safety rules

- Never accept an arbitrary update URL from a remote caller, chat command, MCP request, or manifest field.
- Never execute code directly from the network or from an unverified archive.
- Never disable the watchdog permanently to perform an update.
- Never install third-party software through this updater.
- Never run the same release transaction twice.

## Trust root

The online feed origin is compiled/configured as an allow-listed constant, not supplied by a caller. Initial deployment may use the project-controlled GitHub repository over HTTPS. The updater must reject redirects/final origins outside the allow-list.

The online manifest must be bounded before parsing (<= 100 KB). The package must be bounded before download/hash verification (<= 700 MB).

Every package requires an exact SHA-256 match. If a publisher signing key/certificate is introduced later, signature verification becomes an additional mandatory gate; SHA-256 remains mandatory.

## Feed schema

```json
{
  "schema": 1,
  "channel": "preview",
  "version": "7.9.0-rc2",
  "release_id": "v7.9.0-rc2",
  "min_manager_version": "7.9.0-rc1",
  "package": {
    "asset": "ThayLinh-PC-Control-7.9.0-rc2.zip",
    "size": 12345678,
    "sha256": "<64 lowercase hex chars>"
  },
  "health": {
    "timeout_seconds": 90,
    "required_agent_count": 1,
    "required_relay_count": 1
  }
}
```

The asset name is only a release-asset identifier. The client constructs the final URL from its compiled/allow-listed owner/repository/release origin. The feed cannot provide a raw executable URL.

## Version policy

- Parse versions strictly using SemVer-compatible rules used by V7.9.
- Update only when `feed.version > installed.version` for the selected channel.
- Refuse downgrade through the automatic path.
- Manual recovery may restore `last-known-good` only through the rollback path.
- `release_id + package.sha256` is the idempotency key.

## Check cadence

- Check once after the manager reaches HEALTHY following boot/login.
- Re-check every 6 hours.
- Apply random local jitter of up to 10 minutes to avoid repeated synchronized checks after reconnects.
- Exponential backoff on network errors; network failure must never affect normal PC-control operation.
- When offline, continue operating and retain the local update/recovery path.

## State machine

`IDLE -> CHECKING -> AVAILABLE -> DOWNLOADING -> VERIFIED -> STAGED -> INSTALLING -> HEALTH_CHECK -> COMMITTED`

Failure paths:

- `CHECKING/DOWNLOADING -> IDLE` for ordinary network failures.
- `VERIFIED/STAGED/INSTALLING/HEALTH_CHECK -> ROLLBACK -> HEALTH_CHECK -> ROLLED_BACK` for install/runtime failures.
- If rollback health-check fails, enter existing SAFE MODE and preserve diagnostics.

Persist state atomically so power loss/reboot can resume or roll back safely.

## Versioned installation layout

Prefer side-by-side immutable version directories rather than overwriting the running install:

```text
%LOCALAPPDATA%\ThayLinhPCControl\
  current.json
  versions\
    7.9.0-rc1\
    7.9.0-rc2\
  staging\
  rollback\
  data\
```

`data` contains persistent configuration/identity/secrets/logs and is never replaced by release payloads.

`current.json` is switched atomically only after package verification. The launcher starts the selected version. The old version remains available until the new release passes its health window.

## Install transaction

1. Manager verifies it is HEALTHY and no other update transaction is active.
2. Fetch fixed online manifest with strict timeouts and size cap.
3. Validate schema/channel/version/release id/package metadata.
4. Construct package URL from trusted origin + release id + asset identifier.
5. Download to a new staging file with size limit and timeout.
6. Verify exact size and SHA-256.
7. Extract into a new version directory; reject path traversal, absolute paths, symlinks/reparse-point escapes, and files outside the version root.
8. Validate release inventory and `VERSION.json` before activation.
9. Record `previous_version` and update transaction id atomically.
10. Enter watchdog maintenance/update phase so watchdog does not fight an intentional restart.
11. Atomically switch `current.json` to the staged version.
12. Restart through the existing launcher/manager path.
13. Health-check the new version.
14. Commit on success; retain previous version as last-known-good.
15. On failure, atomically switch back to previous version and restart.

## Health-check gate

A release is not committed merely because its process starts.

Required checks:

- manager/watchdog process healthy
- exactly one intended PC-control agent instance
- exactly one intended relay/gateway instance where applicable
- local status endpoint/IPC answers within timeout
- build/version reported equals staged version
- no immediate restart/crash loop
- protected trust/config files readable
- remote-control command path can initialize without changing user data

The default health window is 90 seconds, configurable only within a bounded safe range.

## Protected persistent data

Release payloads must not overwrite or delete:

- `config.json`
- device identity / machine identity
- secrets/tokens/credentials
- logs and diagnostics
- safe-mode state
- update transaction journal
- last-known-good metadata
- user documents
- maintenance/recovery trust configuration

Migration of persistent data requires an explicit versioned migration with backup and rollback support.

## Local recovery compatibility

The existing local feed remains valid and higher-priority for explicit recovery. It is still hash-pinned and re-verified by TrustedUpdate. Online auto-update must not weaken the current local trust checks.

## Status surface

Expose bounded non-secret fields through the existing status surface:

```json
{
  "currentVersion": "7.9.0-rc1",
  "updateChannel": "preview",
  "updateState": "idle",
  "latestVersion": "7.9.0-rc2",
  "lastCheck": "2026-09-09T18:00:00+07:00",
  "lastUpdate": null,
  "rollbackAvailable": true
}
```

Do not disclose local filesystem paths, feed credentials, tokens, or staging paths.

Optional local/admin-only commands:

- `Update.Check`
- `Update.Status`
- `Update.ApplyStaged`
- `Update.Rollback`

Automatic mode does not require a caller to invoke these commands.

## Observability

Log bounded events only:

- update check started/completed
- version available
- download started/completed
- verification pass/fail
- activation started
- health-check pass/fail
- rollback started/completed

Never log credentials, signed URLs, tokens, or secret config values.

## Acceptance tests

1. No update available -> no process restart, PC Control stays healthy.
2. Offline -> check fails softly, control functions remain available.
3. Oversized manifest -> reject before parsing.
4. Oversized package -> reject before full download/use.
5. Wrong SHA-256 -> reject, never extract/execute.
6. Path traversal in archive -> reject.
7. Feed channel mismatch -> reject.
8. Same release transaction repeated -> `ALREADY_APPLIED`, no reinstall.
9. New version fails start -> automatic rollback to last-known-good.
10. New version starts but health endpoint fails -> rollback.
11. Power loss after staging but before switch -> old version boots.
12. Power loss after switch before commit -> launcher/update journal resolves to health-check or rollback.
13. Config/device identity/secrets unchanged across successful update.
14. Agent/relay duplicate count after update = 0; intended instance count remains exactly one each.
15. Local recovery feed still works with its existing hash-pinned contract.

## Integration rule

This is a V7.9 enhancement. Keep the existing single agent/relay/watchdog topology. The manager/watchdog owns update orchestration; a tiny external bootstrap/launcher helper may be used only to replace/switch binaries that cannot update themselves while running.
