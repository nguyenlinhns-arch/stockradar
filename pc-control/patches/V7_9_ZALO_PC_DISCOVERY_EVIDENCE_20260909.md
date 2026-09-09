# V7.9 Zalo PC — Discovery Evidence 2026-09-09

Status: historical PC-backup evidence only; LIVE revalidation still required.

## Evidence from BACKUP_PC_2026-09-08

Installed-app registry inventory recorded:

- DisplayName: `Zalo 26.08.20`
- DisplayVersion: `26.08.20`
- Publisher: `VNG Corp.`

Backup filesystem confirms the installation root used on 2026-09-08:

`C:\Users\PC\AppData\Local\Programs\Zalo\`

Observed root contents included:

- `Zalo.exe` launcher
- `Uninstall Zalo.exe`
- version directory `Zalo-26.8.20`
- prior version directory `Zalo-26.8.10`
- `resources`
- `sl.exe`
- `Zalo.VisualElementsManifest.xml`

Observed version directory:

`C:\Users\PC\AppData\Local\Programs\Zalo\Zalo-26.8.20\`

Important files included:

- `Zalo.exe` (~136.6 MB)
- `resources`
- `plugins`
- `locales`
- `update_meta.json`
- `chrome_100_percent.pak`
- `chrome_200_percent.pak`
- `resources.pak`
- `icudtl.dat`
- `ffmpeg.dll`
- `LICENSE.electron.txt`
- `LICENSES.chromium.html`

This is strong evidence that the installed Zalo PC build is Electron/Chromium based.

## Architectural consequence

The Zalo PC adapter should NOT be treated as a web-browser automation target.

Accessibility route order is:

1. Windows UI Automation when the current Electron/Chromium build exposes useful UIA nodes/patterns;
2. MSAA/IAccessible/IAccessible2-compatible accessibility route if UIA is incomplete;
3. targeted visual interpretation of the Zalo application/window region;
4. fresh relative keyboard/pointer control only as a last fallback.

Do not add remote-debugging/CDP flags, do not patch Zalo, and do not read its cookies/tokens/private databases.

## Live discovery gate

The historical backup is NOT sufficient to authorize current execution.

Before registering the live `zalo-pc` ManagedApp profile, V7 must on the actual PC:

1. resolve the current installation root through bounded installed-app/known-root discovery;
2. verify the current launcher/version executable exists;
3. record current product/file version;
4. compute/verify local executable identity/hash under V7 policy;
5. launch/focus the exact current app only;
6. identify the real process tree + main window;
7. inspect available accessibility backends and capture a bounded tree/profile;
8. run read-only status/list/search/open/read regression;
9. activate mutation/tag capability only after profile compatibility and read-side regression pass.

If Zalo has updated beyond 26.08.20, the old selector/profile is evidence only and mutation remains blocked until a matching profile passes regression.
