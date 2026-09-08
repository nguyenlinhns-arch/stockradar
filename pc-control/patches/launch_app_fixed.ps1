[CmdletBinding()]
param(
    [Parameter(Position=0)]
    [string]$Name,
    [string]$Action = 'launch',
    [int]$Timeout = 10
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($Name)) {
    throw 'name_required'
}

function Find-ExistingExe {
    param([string[]]$Candidates)
    foreach ($raw in $Candidates) {
        if ([string]::IsNullOrWhiteSpace($raw)) { continue }
        $p = [Environment]::ExpandEnvironmentVariables($raw)
        if (Test-Path -LiteralPath $p -PathType Leaf) {
            return $p
        }
    }
    return $null
}

function Resolve-App {
    param([string]$InputName)
    $key = $InputName.Trim().ToLowerInvariant()

    switch ($key) {
        'calculator' { return @{ file = 'calc.exe'; process = 'CalculatorApp' } }
        'calc'       { return @{ file = 'calc.exe'; process = 'CalculatorApp' } }
        'notepad'    { return @{ file = 'notepad.exe'; process = 'Notepad' } }
        'explorer'   { return @{ file = 'explorer.exe'; process = 'explorer' } }
        'edge'       { return @{ file = 'msedge.exe'; process = 'msedge' } }
        'chrome'     { return @{ file = 'chrome.exe'; process = 'chrome' } }
        'settings'   { return @{ file = 'ms-settings:'; process = 'SystemSettings' } }

        'zalo' {
            $f = Find-ExistingExe @(
                '%LOCALAPPDATA%\Programs\Zalo\Zalo.exe',
                '%LOCALAPPDATA%\Zalo\Zalo.exe'
            )
            if (-not $f) {
                foreach ($r in @(
                    (Join-Path $env:LOCALAPPDATA 'Programs\Zalo'),
                    (Join-Path $env:LOCALAPPDATA 'Zalo')
                )) {
                    if (-not (Test-Path -LiteralPath $r -PathType Container)) { continue }
                    $f = Get-ChildItem -LiteralPath $r -Filter Zalo.exe -File -Recurse -ErrorAction SilentlyContinue |
                         Select-Object -First 1 -ExpandProperty FullName
                    if ($f) { break }
                }
            }
            if (-not $f) { throw 'zalo_not_found' }
            return @{ file = $f; process = 'Zalo' }
        }

        'capcut' {
            $f = Find-ExistingExe @(
                '%LOCALAPPDATA%\CapCut\Apps\CapCut.exe',
                '%LOCALAPPDATA%\Programs\CapCut\CapCut.exe'
            )
            if (-not $f) {
                foreach ($r in @(
                    (Join-Path $env:LOCALAPPDATA 'CapCut'),
                    (Join-Path $env:LOCALAPPDATA 'Programs\CapCut')
                )) {
                    if (-not (Test-Path -LiteralPath $r -PathType Container)) { continue }
                    $f = Get-ChildItem -LiteralPath $r -Filter CapCut.exe -File -Recurse -ErrorAction SilentlyContinue |
                         Sort-Object LastWriteTime -Descending |
                         Select-Object -First 1 -ExpandProperty FullName
                    if ($f) { break }
                }
            }
            if (-not $f) { throw 'capcut_not_found' }
            return @{ file = $f; process = 'CapCut' }
        }

        default {
            $expanded = [Environment]::ExpandEnvironmentVariables($InputName)
            if ([IO.Path]::IsPathRooted($expanded) -and
                [IO.Path]::GetExtension($expanded) -ieq '.exe' -and
                (Test-Path -LiteralPath $expanded -PathType Leaf)) {
                return @{
                    file = $expanded
                    process = [IO.Path]::GetFileNameWithoutExtension($expanded)
                }
            }

            $cmd = Get-Command $InputName -CommandType Application -ErrorAction SilentlyContinue
            if ($cmd -and [IO.Path]::GetExtension($cmd.Source) -ieq '.exe') {
                return @{
                    file = $cmd.Source
                    process = [IO.Path]::GetFileNameWithoutExtension($cmd.Source)
                }
            }

            throw ('app_not_found:' + $InputName)
        }
    }
}

$app = Resolve-App $Name
$mode = $Action.Trim().ToLowerInvariant()

if ($mode -in @('status', 'check')) {
    $running = @(Get-Process -Name $app.process -ErrorAction SilentlyContinue).Count -gt 0
    [pscustomobject]@{
        ok = $true
        name = $Name
        running = $running
        process = $app.process
    } | ConvertTo-Json -Compress
    exit 0
}

if ($mode -notin @('launch', 'start', 'open', '')) {
    throw ('unsupported_action:' + $Action)
}

if ($app.file -eq 'ms-settings:') {
    Start-Process $app.file | Out-Null
} else {
    Start-Process -FilePath $app.file | Out-Null
}

$deadline = (Get-Date).AddSeconds([Math]::Max(1, [Math]::Min($Timeout, 30)))
$running = $false
do {
    Start-Sleep -Milliseconds 250
    $running = @(Get-Process -Name $app.process -ErrorAction SilentlyContinue).Count -gt 0
} while (-not $running -and (Get-Date) -lt $deadline)

[pscustomobject]@{
    ok = $true
    name = $Name
    launched = $true
    running = $running
    process = $app.process
} | ConvertTo-Json -Compress
