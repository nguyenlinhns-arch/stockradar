@echo off
setlocal
set "SCRIPT=%LOCALAPPDATA%\ThayLinhPCBridge\repair_hub.ps1"
if not exist "%SCRIPT%" exit /b 2
powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%SCRIPT%"
exit /b %ERRORLEVEL%
