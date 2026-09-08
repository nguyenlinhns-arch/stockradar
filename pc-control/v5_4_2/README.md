# ThayLinh PC Bridge V5.4.2

V5.4.2 changes the primary command channel from public GitHub Issues to a **private Google Drive/DriveFS bus**.

## Primary path

`ChatGPT -> Google Drive connector -> 07_CHATGPT_PC/PC_CONTROL_BUS/command.json -> Google Drive for desktop -> Windows agent`

Results travel back through the same private folder:

`Windows agent -> LATEST.json / RESULT_*.json / SCREENSHOT_*.png -> DriveFS -> Google Drive -> ChatGPT`

GitHub Issues remains only a restricted rescue fallback. UI typing/click commands are never accepted from public GitHub Issues.

## Why V5.4.2

V5.4.1 could issue rescue commands but could not return private execution results when Remote Desktop Commander was offline. Desktop Commander Remote also requires an OAuth device pairing flow and can fail independently. V5.4.2 therefore makes the Drive bus authoritative and treats Desktop Commander as optional redundancy.

## Drive bus

Cloud folder:

`07_CHATGPT_PC/PC_CONTROL_BUS`

Files:
- `command.json` — written/updated by ChatGPT.
- `LATEST.json` — 30-second heartbeat and latest status from the PC.
- `RESULT_<id>.json` — result for each processed command.
- `SCREENSHOT_<id>.png` — screenshots requested by ChatGPT.
- `INSTALLER_STATUS.json` — installer-level readback even if the main agent fails afterward.

The agent discovers common DriveFS layouts including `G:\My Drive\07_CHATGPT_PC\PC_CONTROL_BUS` and scans mounted filesystem drive letters.

## Private Drive actions

Rescue/app actions:
- `PING`, `STATUS`, `SELF_TEST`, `REPAIR_ALL`
- `START_HUB`
- `START_COMPUTER_USE`, `RESTART_COMPUTER_USE`
- `START_DESKTOP_COMMANDER`, `RESTART_DESKTOP_COMMANDER`
- `START_ZALO`, `FOCUS_ZALO`
- `START_CAPCUT`, `FOCUS_CAPCUT`

Computer-use actions:
- `LIST_WINDOWS`, `ACTIVE_WINDOW`, `FOCUS_WINDOW`
- `MOUSE_POSITION`, `MOVE_MOUSE`
- `CLICK`, `DOUBLE_CLICK`, `RIGHT_CLICK`
- `KEY`
- `TYPE_TEXT` (Unicode, max 10,000 characters)
- `SCREENSHOT`
- `WAIT`
- `BATCH` (up to 50 non-nested steps)

There is no arbitrary shell/PowerShell/command-execution action in the Drive protocol.

## Computer Use recovery

The recovery helper first checks ports 8777 and 8766. It includes the previously verified legacy root `%LOCALAPPDATA%\ThayLinhComputerUse2` and discovers other `ThayLinh*ComputerUse*` roots. It starts only known recovery/start scripts; it does not run installers.

## Desktop Commander

Desktop Commander is optional redundancy. Automatic maintenance starts it only if `%USERPROFILE%\.desktop-commander-device\device.json` already exists. This avoids repeatedly opening an OAuth pairing browser when the device is not paired.

## GitHub fallback

GitHub Issues polling is newest-first and ignores issue numbers below 110 for this release. The fallback accepts rescue/app-start actions only; it never accepts `TYPE_TEXT`, click, screenshot, or batch UI actions.

## Install/upgrade

Run `pc-control/releases/bootstrap_v5_4_2.cmd` once. It upgrades V5.4.1 in place, preserves local state/logs where appropriate, replaces the scheduled task, validates immutable Git blob hashes, starts Hub/Computer Use recovery, starts the bridge, and writes installer readback to Drive when DriveFS is visible.

## Validation

Windows GitHub Actions run `34172096047` passed:
- Python compile
- PowerShell parsing
- static architecture assertions
- actual immutable installer with `-NoStart`
- installed payload verification
- rollback/uninstall
