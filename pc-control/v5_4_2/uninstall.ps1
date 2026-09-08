[CmdletBinding()]
param([switch]$KeepLogs)

$ErrorActionPreference='Continue'
$Root=Join-Path $env:LOCALAPPDATA 'ThayLinhPCBridge'
$TaskName='ThayLinh-PCBridge-V54'
$StartupCmd=Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup\ThayLinh-PCBridge-V54.cmd'
$HubWrapper=Join-Path $env:USERPROFILE '.openai\computer-use\automation_hub.cmd'

try {
 Get-CimInstance Win32_Process | Where-Object {
  $_.ProcessId -ne $PID -and $_.CommandLine -and
  ($_.CommandLine -match '(?i)ThayLinhPCBridge.*agent\.py' -or $_.CommandLine -match '(?i)ThayLinhPCBridge.*run_bridge\.ps1')
 } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
} catch {}
try { Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue } catch {}
try { schtasks.exe /Delete /F /TN $TaskName | Out-Null } catch {}
Remove-Item -Force -LiteralPath $StartupCmd -ErrorAction SilentlyContinue
if(Test-Path -LiteralPath $HubWrapper){
 try {
  $txt=Get-Content -LiteralPath $HubWrapper -Raw -ErrorAction SilentlyContinue
  if($txt -match 'ThayLinhPCBridge\\repair_hub\.ps1'){Remove-Item -Force -LiteralPath $HubWrapper -ErrorAction SilentlyContinue}
 } catch {}
}
if($KeepLogs -and (Test-Path -LiteralPath (Join-Path $Root 'logs'))){
 $backup=Join-Path $env:USERPROFILE ("Downloads\ThayLinhPCBridge-logs-"+(Get-Date -Format 'yyyyMMdd-HHmmss'))
 Copy-Item -Recurse -Force -LiteralPath (Join-Path $Root 'logs') -Destination $backup
 Write-Host "Logs copied to $backup"
}
Remove-Item -Recurse -Force -LiteralPath $Root -ErrorAction SilentlyContinue
Write-Host 'ThayLinh PC Bridge removed. Google Drive PC_CONTROL_BUS data was preserved.'
