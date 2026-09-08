@echo off
setlocal EnableExtensions
set "ROOT=%LOCALAPPDATA%\ThayLinhComputerUseV4"
set "TARGET=%ROOT%\launch_app.ps1"
set "TMP=%TEMP%\ThayLinh_launch_app_fixed.ps1"
set "LOG=%TEMP%\ThayLinh_launch_app_patch.log"

> "%TMP%" (
  echo [CmdletBinding^(^)]
  echo param^
  echo ^(
  echo   [Parameter^(Position=0^)] [string]$Name,
  echo   [string]$Action = 'launch',
  echo   [int]$Timeout = 10
  echo ^)
  echo $ErrorActionPreference = 'Stop'
  echo if ^([string]::IsNullOrWhiteSpace^($Name^)^) { throw 'name_required' }
  echo $key = $Name.Trim^(^).ToLowerInvariant^(^)
  echo function Find-ExistingExe ^([string[]]$Candidates^) {
  echo   foreach ^($raw in $Candidates^) {
  echo     if ^([string]::IsNullOrWhiteSpace^($raw^)^) { continue }
  echo     $p = [Environment]::ExpandEnvironmentVariables^($raw^)
  echo     if ^(Test-Path -LiteralPath $p -PathType Leaf^) { return $p }
  echo   }
  echo   return $null
  echo }
  echo function Resolve-App ^([string]$App^) {
  echo   switch ^($App^) {
  echo     'calculator' { return @{ file = 'calc.exe'; process = 'CalculatorApp' } }
  echo     'calc'       { return @{ file = 'calc.exe'; process = 'CalculatorApp' } }
  echo     'notepad'    { return @{ file = 'notepad.exe'; process = 'Notepad' } }
  echo     'explorer'   { return @{ file = 'explorer.exe'; process = 'explorer' } }
  echo     'edge'       { return @{ file = 'msedge.exe'; process = 'msedge' } }
  echo     'chrome'     { return @{ file = 'chrome.exe'; process = 'chrome' } }
  echo     'settings'   { return @{ file = 'ms-settings:'; process = 'SystemSettings' } }
  echo     'zalo' {
  echo       $f = Find-ExistingExe @^(
  echo         '%%LOCALAPPDATA%%\Programs\Zalo\Zalo.exe',
  echo         '%%LOCALAPPDATA%%\Zalo\Zalo.exe'
  echo       ^)
  echo       if ^(-not $f^) {
  echo         $roots = @^(
  echo           ^(Join-Path $env:LOCALAPPDATA 'Programs\Zalo'^),
  echo           ^(Join-Path $env:LOCALAPPDATA 'Zalo'^)
  echo         ^)
  echo         foreach ^($r in $roots^) { if ^(Test-Path $r^) { $f = Get-ChildItem -LiteralPath $r -Filter Zalo.exe -File -Recurse -ErrorAction SilentlyContinue ^| Select-Object -First 1 -ExpandProperty FullName; if ^($f^) { break } } }
  echo       }
  echo       if ^(-not $f^) { throw 'zalo_not_found' }
  echo       return @{ file = $f; process = 'Zalo' }
  echo     }
  echo     'capcut' {
  echo       $f = Find-ExistingExe @^(
  echo         '%%LOCALAPPDATA%%\CapCut\Apps\CapCut.exe',
  echo         '%%LOCALAPPDATA%%\Programs\CapCut\CapCut.exe'
  echo       ^)
  echo       if ^(-not $f^) {
  echo         $roots = @^(
  echo           ^(Join-Path $env:LOCALAPPDATA 'CapCut'^),
  echo           ^(Join-Path $env:LOCALAPPDATA 'Programs\CapCut'^)
  echo         ^)
  echo         foreach ^($r in $roots^) { if ^(Test-Path $r^) { $f = Get-ChildItem -LiteralPath $r -Filter CapCut.exe -File -Recurse -ErrorAction SilentlyContinue ^| Sort-Object LastWriteTime -Descending ^| Select-Object -First 1 -ExpandProperty FullName; if ^($f^) { break } } }
  echo       }
  echo       if ^(-not $f^) { throw 'capcut_not_found' }
  echo       return @{ file = $f; process = 'CapCut' }
  echo     }
  echo     default {
  echo       $expanded = [Environment]::ExpandEnvironmentVariables^($Name^)
  echo       if ^([IO.Path]::IsPathRooted^($expanded^) -and [IO.Path]::GetExtension^($expanded^) -ieq '.exe' -and ^(Test-Path -LiteralPath $expanded -PathType Leaf^)^) {
  echo         return @{ file = $expanded; process = [IO.Path]::GetFileNameWithoutExtension^($expanded^) }
  echo       }
  echo       $cmd = Get-Command $Name -CommandType Application -ErrorAction SilentlyContinue
  echo       if ^($cmd -and [IO.Path]::GetExtension^($cmd.Source^) -ieq '.exe'^) { return @{ file = $cmd.Source; process = [IO.Path]::GetFileNameWithoutExtension^($cmd.Source^) } }
  echo       throw ^('app_not_found:' + $Name^)
  echo     }
  echo   }
  echo }
  echo $app = Resolve-App $key
  echo $mode = $Action.Trim^(^).ToLowerInvariant^(^)
  echo if ^($mode -in @^('status','check'^)^) {
  echo   $running = @^(Get-Process -Name $app.process -ErrorAction SilentlyContinue^).Count -gt 0
  echo   [pscustomobject]@{ ok = $true; name = $Name; running = $running; process = $app.process } ^| ConvertTo-Json -Compress
  echo   exit 0
  echo }
  echo if ^($mode -notin @^('launch','start','open',''^)^) { throw ^('unsupported_action:' + $Action^) }
  echo if ^($app.file -eq 'ms-settings:'^) { Start-Process $app.file ^| Out-Null }
  echo else { Start-Process -FilePath $app.file ^| Out-Null }
  echo $deadline = ^(Get-Date^).AddSeconds^([Math]::Max^(1,[Math]::Min^($Timeout,30^)^)^)
  echo $running = $false
  echo do {
  echo   Start-Sleep -Milliseconds 250
  echo   $running = @^(Get-Process -Name $app.process -ErrorAction SilentlyContinue^).Count -gt 0
  echo } while ^(-not $running -and ^(Get-Date^) -lt $deadline^)
  echo [pscustomobject]@{ ok = $true; name = $Name; launched = $true; running = $running; process = $app.process } ^| ConvertTo-Json -Compress
)

if not exist "%ROOT%" (
  echo Computer Use root not found: %ROOT%
  exit /b 2
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$t=$null;$e=$null;[System.Management.Automation.Language.Parser]::ParseFile('%TMP%',[ref]$t,[ref]$e)|Out-Null;if($e.Count){$e|%%{Write-Host $_.Message};exit 3}"
if errorlevel 1 exit /b 3

if exist "%TARGET%" copy /y "%TARGET%" "%TARGET%.bak" >nul
copy /y "%TMP%" "%TARGET%" >nul || exit /b 4
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%TARGET%" -Name calculator -Action status -Timeout 2 > "%LOG%" 2>&1
if errorlevel 1 (
  if exist "%TARGET%.bak" copy /y "%TARGET%.bak" "%TARGET%" >nul
  echo Patch self-test failed. See %LOG%
  exit /b 5
)
echo PATCH_OK
type "%LOG%"
exit /b 0
