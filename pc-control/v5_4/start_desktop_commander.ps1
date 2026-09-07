[CmdletBinding()]
param([switch]$Force)

$ErrorActionPreference = 'Continue'
$PinnedFallback = '0.2.48'
$LogRoot = Join-Path $env:LOCALAPPDATA 'ThayLinhPCBridge\logs'
New-Item -ItemType Directory -Force -Path $LogRoot | Out-Null
$LogFile = Join-Path $LogRoot 'desktop-commander-launch.log'

function Log([string]$Message) {
    $line = "$(Get-Date -Format o) $Message"
    Add-Content -LiteralPath $LogFile -Value $line -Encoding UTF8
    Write-Host $line
}

function Get-RemoteProcesses {
    try {
        return @(Get-CimInstance Win32_Process | Where-Object {
            $_.CommandLine -and $_.CommandLine -match '(?i)desktop-commander' -and $_.CommandLine -match '(?i)\bremote\b'
        })
    } catch { return @() }
}

$existing = Get-RemoteProcesses
if ($Force -and $existing.Count -gt 0) {
    Log "Force restart requested; stopping $($existing.Count) existing remote process(es)."
    foreach ($p in $existing) {
        if ($p.ProcessId -ne $PID) { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue }
    }
    Start-Sleep -Seconds 1
} elseif ($existing.Count -gt 0) {
    Log 'Desktop Commander remote already running.'
    exit 0
}

$direct = Get-Command desktop-commander.cmd -ErrorAction SilentlyContinue
if (-not $direct) { $direct = Get-Command desktop-commander.exe -ErrorAction SilentlyContinue }
if (-not $direct) { $direct = Get-Command desktop-commander -ErrorAction SilentlyContinue }

if ($direct) {
    try {
        Log "Launching installed Desktop Commander: $($direct.Source) remote"
        Start-Process -FilePath $direct.Source -ArgumentList @('remote') -WindowStyle Hidden
        Start-Sleep -Seconds 3
        if ((Get-RemoteProcesses).Count -gt 0) { Log 'Installed launcher started remote process.'; exit 0 }
    } catch { Log "Installed launcher failed: $($_.Exception.Message)" }
}

$npx = Get-Command npx.cmd -ErrorAction SilentlyContinue
if (-not $npx) { $npx = Get-Command npx -ErrorAction SilentlyContinue }
if (-not $npx) {
    Log 'npx not found; cannot start pinned fallback.'
    exit 2
}

try {
    Log "Launching pinned fallback @wonderwhy-er/desktop-commander@$PinnedFallback with --prefer-offline."
    Start-Process -FilePath $npx.Source -ArgumentList @('--yes','--prefer-offline',"@wonderwhy-er/desktop-commander@$PinnedFallback",'remote') -WindowStyle Hidden
    Start-Sleep -Seconds 5
    if ((Get-RemoteProcesses).Count -gt 0) { Log 'Pinned fallback started remote process.'; exit 0 }
    Log 'Pinned fallback launched but remote process not detected yet.'
    exit 3
} catch {
    Log "Pinned fallback failed: $($_.Exception.Message)"
    exit 4
}
