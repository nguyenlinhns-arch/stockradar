[CmdletBinding()]
param([switch]$Force)

$ErrorActionPreference = 'Continue'
$LogRoot = Join-Path $env:LOCALAPPDATA 'ThayLinhPCBridge\logs'
New-Item -ItemType Directory -Force -Path $LogRoot | Out-Null
$LogFile = Join-Path $LogRoot 'computer-use-launch.log'
$HealthUrls = @('http://127.0.0.1:8777/health','http://127.0.0.1:8766/health')

function Log([string]$Message) {
    $line = "$(Get-Date -Format o) $Message"
    Add-Content -LiteralPath $LogFile -Value $line -Encoding UTF8
    Write-Host $line
}

function Test-ComputerUse {
    foreach ($url in $HealthUrls) {
        try {
            $resp = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 2
            if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 500) { return $url }
        } catch {}
    }
    return $null
}

function Wait-ComputerUse([int]$Seconds = 12) {
    for ($i=0; $i -lt $Seconds; $i++) {
        $url = Test-ComputerUse
        if ($url) { return $url }
        Start-Sleep -Seconds 1
    }
    return $null
}

$healthy = Test-ComputerUse
if ($healthy -and -not $Force) {
    Log "Computer Use already healthy: $healthy"
    exit 0
}

if ($Force) {
    try {
        $owners = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
            Where-Object { $_.LocalPort -in 8777,8766 } |
            Select-Object -ExpandProperty OwningProcess -Unique
        foreach ($pidValue in $owners) {
            if ($pidValue -and $pidValue -ne $PID) {
                Log "Stopping listener PID $pidValue for force restart."
                Stop-Process -Id $pidValue -Force -ErrorAction SilentlyContinue
            }
        }
        Start-Sleep -Seconds 1
    } catch { Log "Listener cleanup failed: $($_.Exception.Message)" }
}

$roots = New-Object System.Collections.Generic.List[string]
$known = @(
    (Join-Path $env:LOCALAPPDATA 'ThayLinhComputerUse2'),
    (Join-Path $env:LOCALAPPDATA 'ThayLinhComputerUse'),
    (Join-Path $env:LOCALAPPDATA 'ThayLinhComputerUseV5'),
    (Join-Path $env:USERPROFILE '.openai\computer-use')
)
foreach ($r in $known) {
    if ($r -and (Test-Path -LiteralPath $r -PathType Container) -and -not $roots.Contains($r)) { $roots.Add($r) }
}
try {
    Get-ChildItem -LiteralPath $env:LOCALAPPDATA -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match '(?i)^Thay.?Linh.*Computer.?Use' } |
        ForEach-Object { if (-not $roots.Contains($_.FullName)) { $roots.Add($_.FullName) } }
} catch {}

$psNames = @(
    'start_server.ps1','START_SERVER.ps1','start.ps1','START.ps1',
    'BAT_DAU_LAI_V5.ps1','BAT_DAU_LAI_V4_3.ps1','BAT_DAU_LAI.ps1'
)
$cmdNames = @(
    'start_server.cmd','START_SERVER.cmd','start_server.bat','START_SERVER.bat',
    'BAT_DAU_LAI_V5.cmd','BAT_DAU_LAI_V4_3.cmd','BAT_DAU_LAI.cmd',
    'start.cmd','START.cmd','run.cmd','RUN.cmd'
)

foreach ($root in $roots) {
    Log "Inspect Computer Use root: $root"
    foreach ($name in $psNames) {
        $file = Join-Path $root $name
        if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { continue }
        try {
            Log "Starting PowerShell launcher: $file"
            Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',$file) -WorkingDirectory $root -WindowStyle Hidden
            $url = Wait-ComputerUse 12
            if ($url) { Log "Computer Use recovered: $url via $file"; exit 0 }
        } catch { Log "Launcher failed $file : $($_.Exception.Message)" }
    }
    foreach ($name in $cmdNames) {
        $file = Join-Path $root $name
        if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { continue }
        try {
            Log "Starting CMD launcher: $file"
            Start-Process -FilePath 'cmd.exe' -ArgumentList @('/d','/c',$file) -WorkingDirectory $root -WindowStyle Hidden
            $url = Wait-ComputerUse 12
            if ($url) { Log "Computer Use recovered: $url via $file"; exit 0 }
        } catch { Log "Launcher failed $file : $($_.Exception.Message)" }
    }
}

Log 'Computer Use recovery exhausted safe candidates; 8777/8766 remain unavailable.'
exit 1
