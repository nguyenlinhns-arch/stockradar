@echo off
setlocal EnableExtensions
set "ROOT=%LOCALAPPDATA%\ThayLinhComputerUseV4"
set "TARGET=%ROOT%\launch_app.ps1"
set "TMP=%TEMP%\ThayLinh_launch_app_fixed.ps1"
set "LOG=%TEMP%\ThayLinh_launch_app_patch.log"
set "PAYLOAD_COMMIT=ce991f2812f326432ec068c1d9569e1f5ed71c0d"
set "PAYLOAD_URL=https://raw.githubusercontent.com/nguyenlinhns-arch/stockradar/%PAYLOAD_COMMIT%/pc-control/patches/launch_app_fixed.ps1"
set "EXPECTED_SHA256=82457b979dd53dcf4f2fe26297500ccf155aebf84c824b5dde710fbcbfba6ae3"

if not exist "%ROOT%" (
  echo Computer Use root not found: %ROOT%
  exit /b 2
)

echo [1/4] Downloading immutable launcher payload...
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "try { Invoke-WebRequest -UseBasicParsing -Uri '%PAYLOAD_URL%' -OutFile '%TMP%' -TimeoutSec 30 } catch { Write-Error $_; exit 10 }"
if errorlevel 1 exit /b 10

echo [2/4] Verifying SHA-256 and PowerShell syntax...
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$h=(Get-FileHash -Algorithm SHA256 -LiteralPath '%TMP%').Hash.ToLowerInvariant(); if($h -ne '%EXPECTED_SHA256%'){Write-Error ('SHA256 mismatch: '+$h);exit 11}; $t=$null;$e=$null;[System.Management.Automation.Language.Parser]::ParseFile('%TMP%',[ref]$t,[ref]$e)|Out-Null;if($e.Count){$e|ForEach-Object{Write-Error $_.Message};exit 12};Write-Host ('Integrity OK '+$h)"
if errorlevel 1 exit /b 12

echo [3/4] Backing up and installing launcher...
if exist "%TARGET%" copy /y "%TARGET%" "%TARGET%.bak" >nul
copy /y "%TMP%" "%TARGET%" >nul || exit /b 13

echo [4/4] Running non-destructive self-test...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%TARGET%" -Name calculator -Action status -Timeout 2 > "%LOG%" 2>&1
if errorlevel 1 (
  if exist "%TARGET%.bak" copy /y "%TARGET%.bak" "%TARGET%" >nul
  echo Patch self-test failed. Original launcher restored.
  type "%LOG%"
  exit /b 14
)

echo PATCH_OK
type "%LOG%"
exit /b 0
