[CmdletBinding()]
param(
    [switch]$NoStart
)

$ErrorActionPreference = 'Stop'
$Version = '5.4.1'
$RepoRaw = 'https://raw.githubusercontent.com/nguyenlinhns-arch/stockradar/pc-control/pc-control/v5_4'
$ExpectedAgentGitBlob = '038d2c7868b19107f798c1cf11447c99683c51e3'
$ExpectedConfigGitBlob = 'd13e1a750b1fb073813c3e17de275a525385339b'
$Root = Join-Path $env:LOCALAPPDATA 'ThayLinhPCBridge'
$LogDir = Join-Path $Root 'logs'
$TaskName = 'ThayLinh-PCBridge-V54'
$StartupDir = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup'
$StartupCmd = Join-Path $StartupDir 'ThayLinh-PCBridge-V54.cmd'
$InstallLog = Join-Path $env:TEMP 'ThayLinh-PCBridge-V54-install.log'

function Write-InstallLog([string]$Message) {
    $line = "$(Get-Date -Format o) $Message"
    Write-Host $line
    Add-Content -LiteralPath $InstallLog -Value $line -Encoding UTF8
}

function Download-Text([string]$Url, [string]$OutFile) {
    Write-InstallLog "Download $Url"
    Invoke-WebRequest -UseBasicParsing -Uri $Url -OutFile $OutFile -TimeoutSec 30
    if (-not (Test-Path -LiteralPath $OutFile)) { throw "Download failed: $Url" }
    if ((Get-Item -LiteralPath $OutFile).Length -lt 10) { throw "Downloaded file too small: $OutFile" }
}

function Get-GitBlobSha1([string]$Path) {
    $bytes = [System.IO.File]::ReadAllBytes($Path)
    $headerText = 'blob ' + $bytes.Length + [char]0
    $header = [System.Text.Encoding]::ASCII.GetBytes($headerText)
    $all = New-Object byte[] ($header.Length + $bytes.Length)
    [System.Buffer]::BlockCopy($header, 0, $all, 0, $header.Length)
    [System.Buffer]::BlockCopy($bytes, 0, $all, $header.Length, $bytes.Length)
    $sha1 = [System.Security.Cryptography.SHA1]::Create()
    try {
        return (($sha1.ComputeHash($all) | ForEach-Object { $_.ToString('x2') }) -join '')
    } finally {
        $sha1.Dispose()
    }
}

function Assert-GitBlob([string]$Path, [string]$Expected) {
    $actual = Get-GitBlobSha1 $Path
    if ($actual -ne $Expected) {
        throw "Integrity check failed for $Path. Expected $Expected, got $actual"
    }
    Write-InstallLog "Integrity OK: $([System.IO.Path]::GetFileName($Path)) $actual"
}

New-Item -ItemType Directory -Force -Path $Root, $LogDir, $StartupDir | Out-Null
Write-InstallLog "Installing ThayLinh PC Bridge v$Version into $Root"

$agentTmp = Join-Path $env:TEMP 'ThayLinh-PCBridge-agent.py.tmp'
$configTmp = Join-Path $env:TEMP 'ThayLinh-PCBridge-config.json.tmp'
Download-Text "$RepoRaw/agent.py" $agentTmp
Download-Text "$RepoRaw/config.json" $configTmp
Assert-GitBlob $agentTmp $ExpectedAgentGitBlob
Assert-GitBlob $configTmp $ExpectedConfigGitBlob

$python = Get-Command python.exe -ErrorAction SilentlyContinue
$py = Get-Command py.exe -ErrorAction SilentlyContinue
if ($python) {
    & $python.Source -m py_compile $agentTmp
    if ($LASTEXITCODE -ne 0) { throw 'agent.py failed Python syntax check' }
} elseif ($py) {
    & $py.Source -3 -m py_compile $agentTmp
    if ($LASTEXITCODE -ne 0) { throw 'agent.py failed Python syntax check' }
} else {
    throw 'Python 3 was not found. Existing Computer Use/Automation Hub requires Python; repair that installation first.'
}
Write-InstallLog 'Python syntax check OK.'

Move-Item -Force -LiteralPath $agentTmp -Destination (Join-Path $Root 'agent.py')
if (-not (Test-Path -LiteralPath (Join-Path $Root 'config.json'))) {
    Move-Item -Force -LiteralPath $configTmp -Destination (Join-Path $Root 'config.json')
} else {
    Remove-Item -Force -LiteralPath $configTmp -ErrorAction SilentlyContinue
    Write-InstallLog 'Existing config.json preserved.'
}

$runner = @'
$ErrorActionPreference = 'Continue'
$Root = Join-Path $env:LOCALAPPDATA 'ThayLinhPCBridge'
$Agent = Join-Path $Root 'agent.py'
$LogDir = Join-Path $Root 'logs'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$stdout = Join-Path $LogDir 'runner-out.log'
$stderr = Join-Path $LogDir 'runner-err.log'
if (-not (Test-Path -LiteralPath $Agent)) { exit 2 }

$pythonw = Get-Command pythonw.exe -ErrorAction SilentlyContinue
$python = Get-Command python.exe -ErrorAction SilentlyContinue
$py = Get-Command py.exe -ErrorAction SilentlyContinue

if ($pythonw) {
    Start-Process -FilePath $pythonw.Source -ArgumentList @($Agent) -WorkingDirectory $Root -WindowStyle Hidden
    exit 0
}
if ($python) {
    Start-Process -FilePath $python.Source -ArgumentList @($Agent) -WorkingDirectory $Root -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    exit 0
}
if ($py) {
    Start-Process -FilePath $py.Source -ArgumentList @('-3', $Agent) -WorkingDirectory $Root -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    exit 0
}
exit 3
'@
Set-Content -LiteralPath (Join-Path $Root 'run_bridge.ps1') -Value $runner -Encoding UTF8

$repair = @'
@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%LOCALAPPDATA%\ThayLinhPCBridge\run_bridge.ps1"
timeout /t 3 /nobreak >nul
powershell.exe -NoProfile -Command "try { (Invoke-RestMethod -Uri 'http://127.0.0.1:4321/status' -TimeoutSec 5) | ConvertTo-Json -Depth 8 } catch { Write-Host $_.Exception.Message; exit 1 }"
endlocal
'@
Set-Content -LiteralPath (Join-Path $Root 'REPAIR_NOW.cmd') -Value $repair -Encoding ASCII

$startup = @'
@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%LOCALAPPDATA%\ThayLinhPCBridge\run_bridge.ps1"
'@
Set-Content -LiteralPath $StartupCmd -Value $startup -Encoding ASCII

$taskCommand = "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$Root\run_bridge.ps1`""
try {
    & schtasks.exe /Create /F /SC ONLOGON /TN $TaskName /TR $taskCommand /RL LIMITED | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-InstallLog "Scheduled task created: $TaskName"
    } else {
        Write-InstallLog "Scheduled task creation returned $LASTEXITCODE; Startup fallback remains active."
    }
} catch {
    Write-InstallLog "Scheduled task creation failed: $($_.Exception.Message). Startup fallback remains active."
}

$marker = @{
    installed_version = $Version
    installed_at = (Get-Date -Format o)
    install_root = $Root
    task_name = $TaskName
    startup_cmd = $StartupCmd
    agent_git_blob = $ExpectedAgentGitBlob
    config_git_blob = $ExpectedConfigGitBlob
} | ConvertTo-Json -Depth 4
Set-Content -LiteralPath (Join-Path $Root 'install_state.json') -Value $marker -Encoding UTF8

if (-not $NoStart) {
    Write-InstallLog 'Starting bridge now.'
    $runnerPath = Join-Path $Root 'run_bridge.ps1'
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File $runnerPath
    Start-Sleep -Seconds 4
    try {
        $health = Invoke-RestMethod -Uri 'http://127.0.0.1:4321/health' -TimeoutSec 5
        Write-InstallLog ("Health OK: " + ($health | ConvertTo-Json -Compress))
    } catch {
        Write-InstallLog "Bridge did not answer local health yet: $($_.Exception.Message)"
    }
}

Write-InstallLog 'Install completed. The bridge will also start at Windows logon.'
Write-Host "`nInstalled: $Root"
Write-Host "Local health: http://127.0.0.1:4321/health"
Write-Host "Local status: http://127.0.0.1:4321/status"
Write-Host "Repair command: $Root\REPAIR_NOW.cmd"
