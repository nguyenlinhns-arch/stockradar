@echo off
setlocal EnableExtensions
set "PS1=%TEMP%\INSTALL_THAI_LINH_PC_BRIDGE_V5_4.ps1"
set "URL=https://raw.githubusercontent.com/nguyenlinhns-arch/stockradar/pc-control/pc-control/v5_4/install.ps1"
echo [V5.4] Downloading recovery/control installer...
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "try { Invoke-WebRequest -UseBasicParsing -Uri '%URL%' -OutFile '%PS1%' -TimeoutSec 30 } catch { Write-Error $_; exit 1 }"
if errorlevel 1 goto :fail
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%PS1%"
if errorlevel 1 goto :fail
echo.
echo [V5.4] Installation complete.
exit /b 0
:fail
echo.
echo [V5.4] Installation failed. Check %%TEMP%%\ThayLinh-PCBridge-V54-install.log
exit /b 1
