[CmdletBinding()]
param([switch]$Force,[switch]$AllowPairing)

$ErrorActionPreference = 'Continue'
$PinnedFallback = '0.2.48'
$LogRoot = Join-Path $env:LOCALAPPDATA 'ThayLinhPCBridge\logs'
New-Item -ItemType Directory -Force -Path $LogRoot | Out-Null
$LogFile = Join-Path $LogRoot 'desktop-commander-launch.log'
$DeviceFile = Join-Path $env:USERPROFILE '.desktop-commander-device\device.json'

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
    foreach ($p in $existing) { if ($p.ProcessId -ne $PID) { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue } }
    Start-Sleep -Seconds 1
} elseif ($existing.Count -gt 0) {
    Log 'Desktop Commander remote already running.'
    exit 0
}

if (-not (Test-Path -LiteralPath $DeviceFile) -and -not $AllowPairing) {
    Log 'No paired Desktop Commander device file. Skipping automatic browser pairing.'
    exit 5
}

$direct = Get-Command desktop-commander.cmd -ErrorAction SilentlyContinue
if (-not $direct) { $direct = Get-Command desktop-commander.exe -ErrorAction SilentlyContinue }
if (-not $direct) { $direct = Get-Command desktop-commander -ErrorAction SilentlyContinue }
if ($direct) {
    try {
        Log "Launching installed Desktop Commander: $($direct.Source) remote"
        Start-Process -FilePath $direct.Source -ArgumentList @('remote') -WindowStyle Hidden
        Start-Sleep -Seconds 4
        if ((Get-RemoteProcesses).Count -gt 0) { Log 'Installed launcher started remote process.'; exit 0 }
    } catch { Log "Installed launcher failed: $($_.Exception.Message)" }
}

$npx = Get-Command npx.cmd -ErrorAction SilentlyContinue
if (-not $npx) { $npx = Get-Command npx -ErrorAction SilentlyContinue }
if (-not $npx) { Log 'npx not found.'; exit 2 }
try {
    Log "Launching pinned fallback @wonderwhy-er/desktop-commander@$PinnedFallback."
    Start-Process -FilePath $npx.Source -ArgumentList @('--yes','--prefer-offline',"@wonderwhy-er/desktop-commander@$PinnedFallback",'remote') -WindowStyle Hidden
    Start-Sleep -Seconds 6
    if ((Get-RemoteProcesses).Count -gt 0) { Log 'Pinned fallback started remote process.'; exit 0 }
    Log 'Pinned fallback exited or remote process was not detected.'
    exit 3
} catch { Log "Pinned fallback failed: $($_.Exception.Message)"; exit 4 }
