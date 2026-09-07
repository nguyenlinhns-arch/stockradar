# ThayLinh PC Bridge V5.4 — Rescue/Control Layer

V5.4 is an additive recovery layer for the existing V5 Computer Use package. It does **not** replace Automation Hub on port 4310 or the existing V5 UI controller.

## Why this layer exists

The previous stack could lose all remote control when the Remote Desktop Commander connection was down. V5.4 adds a separate Windows-logon agent that can restore the local Hub and Desktop Commander without depending on Opera or Codex.

## Architecture

1. **Local V5 core** remains the primary UI controller.
2. **Automation Hub 4310** remains the stable local health/control surface.
3. **V5.4 rescue agent** runs in the logged-on Windows user session and exposes only `127.0.0.1:4321`.
4. **GitHub Issues rescue bus** is the cloud fallback. The agent accepts only issues created by `nguyenlinhns-arch` and only titles beginning `[PC-CONTROL]` or `[ZALO-CONTROL]`.
5. The agent has a strict action allow-list. There is no arbitrary remote shell in this rescue layer.

## Allowed rescue actions

- `PING`
- `STATUS` / `SELF_TEST`
- `START_HUB`
- `START_DESKTOP_COMMANDER`
- `RESTART_DESKTOP_COMMANDER`
- `START_ZALO`
- `FOCUS_ZALO`
- `START_CAPCUT`
- `FOCUS_CAPCUT`
- `REPAIR_ALL`
- Legacy `ZALO_STATUS` is mapped to `SELF_TEST`.

Example issue title:

`[PC-CONTROL] REPAIR_ALL`

If a GitHub token is available from `THAYLINH_GITHUB_TOKEN`, `GH_TOKEN`, `GITHUB_TOKEN`, or `gh auth token`, the agent posts the JSON result back to the issue and closes it. No token is written into this repository or config file.

## Local endpoints

- `GET http://127.0.0.1:4321/health`
- `GET http://127.0.0.1:4321/status`

The service binds to loopback only; it is not exposed on the LAN or Internet.

## Installation

Run `bootstrap_v5_4.cmd` once on the Windows PC. The installer:

- downloads and syntax-checks `agent.py`;
- preserves an existing `config.json`;
- installs under `%LOCALAPPDATA%\ThayLinhPCBridge`;
- creates a current-user logon Scheduled Task;
- also creates a Startup-folder fallback;
- starts the bridge immediately and checks local health.

Manual repair after installation:

`%LOCALAPPDATA%\ThayLinhPCBridge\REPAIR_NOW.cmd`

## Reliability choices

- single-instance process lock;
- Task Scheduler + Startup fallback;
- Hub health check every two minutes;
- Desktop Commander process detection and restart;
- action idempotency by processed GitHub issue number;
- local state and daily logs;
- last 500 issue IDs retained to prevent replay;
- no Opera dependency;
- no Codex dependency;
- no raw remote command execution.

## Removal

Run `uninstall.ps1`. Use `-KeepLogs` to copy logs to Downloads before removal.
