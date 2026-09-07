[CmdletBinding()]
param([switch]$KeepLogs)

$ErrorActionPreference = 'Continue'
$Root = Join-Path $env:LOCALAPPDATA 'ThayLinhPCBridge'
$TaskName = 'ThayLinh-PCBridge-V54'
$StartupCmd = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup\ThayLinh-PCBridge-V54.cmd'

try {
    Get-CimInstance Win32_Process | Where-Object {
        $_.CommandLine -and $_.CommandLine -like '*ThayLinhPCBridge*agent.py*'
    } | ForEach-Object {
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
} catch {}

try { schtasks.exe /Delete /F /TN $TaskName | Out-Null } catch {}
Remove-Item -Force -LiteralPath $StartupCmd -ErrorAction SilentlyContinue

if ($KeepLogs -and (Test-Path -LiteralPath (Join-Path $Root 'logs'))) {
    $backup = Join-Path $env:USERPROFILE ("Downloads\ThayLinhPCBridge-logs-" + (Get-Date -Format 'yyyyMMdd-HHmmss'))
    Copy-Item -Recurse -Force -LiteralPath (Join-Path $Root 'logs') -Destination $backup
    Write-Host "Logs copied to $backup"
}

Remove-Item -Recurse -Force -LiteralPath $Root -ErrorAction SilentlyContinue
Write-Host 'ThayLinh PC Bridge V5.4 rescue layer removed.'
