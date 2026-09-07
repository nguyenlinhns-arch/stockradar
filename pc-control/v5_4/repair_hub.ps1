[CmdletBinding()]
param()

$ErrorActionPreference = 'Continue'
$HealthUrls = @(
    'http://127.0.0.1:4310/',
    'http://127.0.0.1:4310/admin'
)
$LogRoot = Join-Path $env:LOCALAPPDATA 'ThayLinhPCBridge\logs'
New-Item -ItemType Directory -Force -Path $LogRoot | Out-Null
$LogFile = Join-Path $LogRoot 'hub-repair.log'

function Log([string]$Message) {
    $line = "$(Get-Date -Format o) $Message"
    Add-Content -LiteralPath $LogFile -Value $line -Encoding UTF8
    Write-Host $line
}

function Test-Hub {
    foreach ($url in $HealthUrls) {
        try {
            $resp = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 3
            if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 500) {
                return $true
            }
        } catch {}
    }
    return $false
}

function Wait-Hub([int]$Seconds = 12) {
    for ($i = 0; $i -lt $Seconds; $i++) {
        if (Test-Hub) { return $true }
        Start-Sleep -Seconds 1
    }
    return $false
}

function Start-Detached([string]$FilePath, [string[]]$Arguments, [string]$WorkingDirectory) {
    try {
        Log "START $FilePath $($Arguments -join ' ') cwd=$WorkingDirectory"
        Start-Process -FilePath $FilePath -ArgumentList $Arguments -WorkingDirectory $WorkingDirectory -WindowStyle Hidden
        return $true
    } catch {
        Log "START FAILED: $($_.Exception.Message)"
        return $false
    }
}

if (Test-Hub) {
    Log 'Hub 4310 already healthy.'
    exit 0
}

$roots = New-Object System.Collections.Generic.List[string]
$known = @(
    'D:\Thay_Linh_Automation_Hub_MOI_HOAN_TOAN_v1.3.3',
    'D:\Thay_Linh_Automation_Hub_MOI_HOAN_TOAN_v1.3.2',
    'D:\Thay_Linh_Automation_Hub_MOI_HOAN_TOAN_v1.3.1',
    'D:\Thay_Linh_Automation_Hub',
    (Join-Path $env:USERPROFILE 'Desktop\Thay_Linh_Automation_Hub'),
    (Join-Path $env:LOCALAPPDATA 'ThayLinhAutomationHub')
)
foreach ($r in $known) {
    if ($r -and (Test-Path -LiteralPath $r -PathType Container)) { $roots.Add($r) }
}

foreach ($drive in @('D:\','C:\')) {
    if (-not (Test-Path -LiteralPath $drive)) { continue }
    try {
        Get-ChildItem -LiteralPath $drive -Directory -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -match '(?i)(Thay.?Linh.*Automation.*Hub|Automation.*Hub)' } |
            Select-Object -First 10 |
            ForEach-Object {
                if (-not $roots.Contains($_.FullName)) { $roots.Add($_.FullName) }
            }
    } catch {}
}

$launcherNames = @(
    'START_HUB.cmd','START_HUB.bat','start_hub.cmd','start_hub.bat',
    'START_AUTOMATION_HUB.cmd','START_AUTOMATION_HUB.bat',
    'start_server.cmd','start_server.bat','run_hub.cmd','run_hub.bat',
    'start.cmd','run.cmd'
)

foreach ($root in $roots) {
    Log "Inspect root: $root"
    foreach ($name in $launcherNames) {
        $file = Join-Path $root $name
        if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { continue }
        if (Start-Detached 'cmd.exe' @('/d','/c',$file) $root) {
            if (Wait-Hub 12) { Log "Hub recovered by $file"; exit 0 }
        }
    }

    foreach ($psName in @('START_HUB.ps1','start_hub.ps1','start_server.ps1','run_hub.ps1')) {
        $file = Join-Path $root $psName
        if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { continue }
        if (Start-Detached 'powershell.exe' @('-NoProfile','-ExecutionPolicy','Bypass','-File',$file) $root) {
            if (Wait-Hub 12) { Log "Hub recovered by $file"; exit 0 }
        }
    }

    $package = Join-Path $root 'package.json'
    if (Test-Path -LiteralPath $package -PathType Leaf) {
        try {
            $pkg = Get-Content -LiteralPath $package -Raw | ConvertFrom-Json
            $startScript = $pkg.scripts.start
            $portEvidence = Get-ChildItem -LiteralPath $root -File -Include *.js,*.cjs,*.mjs,*.json -ErrorAction SilentlyContinue |
                Select-String -Pattern '4310' -SimpleMatch -Quiet
            if ($startScript -and $portEvidence) {
                $npm = Get-Command npm.cmd -ErrorAction SilentlyContinue
                if ($npm -and (Start-Detached $npm.Source @('start','--silent') $root)) {
                    if (Wait-Hub 15) { Log "Hub recovered by npm start in $root"; exit 0 }
                }
            }
        } catch { Log "package.json inspect failed: $($_.Exception.Message)" }
    }

    try {
        $scripts = Get-ChildItem -LiteralPath $root -File -Recurse -Depth 2 -Include *.py,*.js,*.cjs,*.mjs -ErrorAction SilentlyContinue |
            Where-Object { $_.Length -lt 5MB } |
            Select-Object -First 300
        foreach ($script in $scripts) {
            $text = Get-Content -LiteralPath $script.FullName -Raw -ErrorAction SilentlyContinue
            if (-not $text -or $text -notmatch '4310') { continue }
            if ($script.Extension -eq '.py' -and $text -match '(?i)(flask|fastapi|uvicorn|HTTPServer|app\.run|serve)') {
                $python = Get-Command python.exe -ErrorAction SilentlyContinue
                if ($python -and (Start-Detached $python.Source @($script.FullName) $script.DirectoryName)) {
                    if (Wait-Hub 15) { Log "Hub recovered by Python $($script.FullName)"; exit 0 }
                }
            }
            if ($script.Extension -in @('.js','.cjs','.mjs') -and $text -match '(?i)(listen\s*\(|createServer|express\s*\()') {
                $node = Get-Command node.exe -ErrorAction SilentlyContinue
                if ($node -and (Start-Detached $node.Source @($script.FullName) $script.DirectoryName)) {
                    if (Wait-Hub 15) { Log "Hub recovered by Node $($script.FullName)"; exit 0 }
                }
            }
        }
    } catch { Log "Script discovery failed in $root: $($_.Exception.Message)" }
}

Log 'Hub recovery exhausted safe candidates; 4310 is still unavailable.'
exit 1
