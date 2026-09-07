@echo off
setlocal EnableExtensions
set "PS1=%TEMP%\INSTALL_THAI_LINH_PC_BRIDGE_V5_4_1.ps1"
set "INSTALLER_COMMIT=16332138dea9d1e74ae085902f946e7152bc233b"
set "URL=https://raw.githubusercontent.com/nguyenlinhns-arch/stockradar/%INSTALLER_COMMIT%/pc-control/v5_4/install.ps1"
echo [V5.4.1] Downloading immutable recovery/control installer...
echo [V5.4.1] Installer commit: %INSTALLER_COMMIT%
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "try { Invoke-WebRequest -UseBasicParsing -Uri '%URL%' -OutFile '%PS1%' -TimeoutSec 30 } catch { Write-Error $_; exit 1 }"
if errorlevel 1 goto :fail
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%PS1%"
if errorlevel 1 goto :fail
echo.
echo [V5.4.1] Installation complete.
exit /b 0
:fail
echo.
echo [V5.4.1] Installation failed. Check %%TEMP%%\ThayLinh-PCBridge-V54-install.log
exit /b 1
