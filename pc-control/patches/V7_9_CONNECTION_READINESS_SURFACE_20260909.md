# V7.9 — Compact connection/readiness surface

Date: 2026-09-09
Status: design/review; integrate through self-maintenance after bootstrap gates

## Problem

V7 has already demonstrated real normal-ChatGPT control and real reboot/logon automatic gateway reconnection, while Remote Desktop Commander can be offline independently. A future session therefore needs a fast way to distinguish:

- ChatGPT/plugin tool not loaded in the current conversation;
- gateway reachable but device offline;
- device heartbeat stale;
- lease not owned;
- watchdog unhealthy;
- GUI desktop locked/not interactive;
- updater/maintenance temporarily preventing mutation;
- fully ready.

Do not use RDC availability as the authority for V7 health.

## Goal

Once the ThayLinh PC Control plugin is loaded in a ChatGPT conversation, one compact read-only call should answer from gateway state even when the Windows device is offline.

Preferred public semantic tool: `pc.connection_info` (or keep the already existing equivalent and tighten its contract rather than adding a duplicate).

## Compact response

Example:

```json
{
  "ok": true,
  "state": "READY",
  "gateway": "READY",
  "device": "ONLINE",
  "heartbeat_age_ms": 3200,
  "lease": "OWNED",
  "watchdog": "PASS",
  "agent_version": "7.9.0-rc1",
  "protocol": 2,
  "filesystem_ready": true,
  "gui_ready": true,
  "interactive_session": "UNLOCKED",
  "maintenance": "IDLE",
  "update": "IDLE",
  "production_ready": false
}
```

Bound the response to a small fixed schema. No full tool catalog, no local paths, no tokens, no DPAPI/key material, no usernames, no recent commands/user content.

## State codes

Top-level `state` is one of:

- `READY`
- `DEVICE_OFFLINE`
- `HEARTBEAT_STALE`
- `LEASE_NOT_OWNED`
- `WATCHDOG_UNHEALTHY`
- `GUI_NOT_READY`
- `MAINTENANCE_BUSY`
- `UPDATE_BUSY`
- `AUTH_ERROR`
- `DEGRADED`

The gateway should return a useful status even when no device RPC can be completed. Do not wait for a device command timeout merely to report offline.

## Reuse existing heartbeat/lease traffic

Do not add an unnecessary second heartbeat loop if the existing worker lease/poll/renewal path already updates a current timestamp.

Prefer to piggyback these bounded fields on the existing authenticated worker presence record:

- last heartbeat timestamp;
- agent build/protocol;
- watchdog health summary;
- interactive session/GUI readiness;
- maintenance/update state.

Gateway computes heartbeat age using server time. This avoids trusting a potentially skewed client wall clock for online/offline classification.

## Reconnect behavior

On worker startup or network recovery:

1. load stable DPAPI identity/lease owner;
2. establish persistent HTTPS session;
3. register/renew presence and lease immediately;
4. publish compact health before waiting for ordinary command traffic;
5. resume normal claim/poll/wake path;
6. use bounded exponential backoff + jitter on network failure;
7. never create a second competing worker simply because cloud connectivity is temporarily lost.

Do not re-pair OAuth/device identity after ordinary reboot/network reconnect.

## GUI readiness

Separate device-online from GUI-ready.

Examples:
- worker online + Windows desktop unlocked -> `filesystem_ready=true`, `gui_ready=true`;
- worker online + desktop locked/secure desktop -> non-GUI operations may remain available but `gui_ready=false`;
- user-active guard may temporarily deny mutation without marking the device offline.

Do not fight the user for input. `USER_ACTIVE_RETRY_LATER` remains a safety result, not a connection failure.

## Fast failure behavior

If gateway state already proves the device is offline/stale/not lease owner, mutation tools should fail quickly with the corresponding stable code instead of holding an enqueue/claim timeout.

If device status is uncertain but might recover, a READ-only connection check may return `DEGRADED` with bounded age/reason. Do not invent success.

## ChatGPT routing guidance

Normal control path remains:

`ChatGPT -> ThayLinh PC Control plugin -> HTTPS gateway -> outbound Windows worker`

Operational policy:
- do NOT add `pc.connection_info` before every healthy command; that creates an extra cloud round trip;
- use it on session start when readiness is genuinely unknown, after a connection-related failure, or when the user explicitly asks status;
- once a task is known and health is current, prefer `pc.execute_task` batching.

## Platform boundary

V7 can make gateway/device readiness observable once the plugin is loaded. It cannot force the ChatGPT product to inject an installed custom plugin's tools into every conversation if the platform has not loaded that app for the current session.

Therefore distinguish:
- **plugin/tool loading problem**: no V7 tool is callable in the conversation at all;
- **V7 runtime problem**: tool is callable and returns device/gateway state.

Do not misdiagnose the first as a dead Windows agent.

## Acceptance

1. Plugin-loaded + device healthy -> compact `READY` in one gateway call.
2. Device powered off -> `DEVICE_OFFLINE` quickly without device command timeout.
3. Stale heartbeat -> deterministic `HEARTBEAT_STALE`.
4. Duplicate/other lease owner -> `LEASE_NOT_OWNED` and no mutation dispatch.
5. Worker online but desktop locked -> device ONLINE, filesystem state truthful, `gui_ready=false`.
6. Watchdog failure -> `WATCHDOG_UNHEALTHY` even if process heartbeat exists.
7. Maintenance/update transaction -> state exposed without leaking paths/candidate data.
8. Reboot/network reconnect returns to READY using existing identity without re-pairing.
9. Response remains small and contains no tool schemas/secrets/user content.
10. RDC offline has no effect on V7 readiness classification.
