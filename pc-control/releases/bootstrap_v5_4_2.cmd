@echo off
setlocal EnableExtensions
set "PS1=%TEMP%\INSTALL_THAI_LINH_PC_BRIDGE_V5_4_2.ps1"
set "INSTALLER_COMMIT=18a3c2d9c450a5d0bf79041d7fefd8b1829e9f69"
set "URL=https://raw.githubusercontent.com/nguyenlinhns-arch/stockradar/%INSTALLER_COMMIT%/pc-control/v5_4_2/install.ps1"
echo [V5.4.2] Upgrading to private Google Drive PC control bus...
echo [V5.4.2] Installer commit: %INSTALLER_COMMIT%
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "try { Invoke-WebRequest -UseBasicParsing -Uri '%URL%' -OutFile '%PS1%' -TimeoutSec 30 } catch { Write-Error $_; exit 1 }"
if errorlevel 1 goto :fail
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%PS1%"
if errorlevel 1 goto :fail
echo.
echo [V5.4.2] Upgrade complete. ChatGPT can validate through Google Drive PC_CONTROL_BUS.
exit /b 0
:fail
echo.
echo [V5.4.2] Upgrade failed. Check %%TEMP%%\ThayLinh-PCBridge-V542-install.log
exit /b 1
