[CmdletBinding()]
param()

$ErrorActionPreference = 'Continue'
$HealthUrls = @('http://127.0.0.1:4310/','http://127.0.0.1:4310/admin')
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
            $r=Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 3
            if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500) { return $true }
        } catch {}
    }
    return $false
}
function Wait-Hub([int]$Seconds=12) {
    for($i=0;$i -lt $Seconds;$i++){ if(Test-Hub){return $true}; Start-Sleep 1 }
    return $false
}
function Start-Detached([string]$File,[string[]]$Args,[string]$Cwd){
    try { Start-Process -FilePath $File -ArgumentList $Args -WorkingDirectory $Cwd -WindowStyle Hidden; return $true }
    catch { Log "START FAILED $File : $($_.Exception.Message)"; return $false }
}

if(Test-Hub){ Log 'Hub 4310 already healthy.'; exit 0 }

$roots=New-Object System.Collections.Generic.List[string]
$known=@(
 'D:\Thay_Linh_Automation_Hub_MOI_HOAN_TOAN_v1.3.3',
 'D:\Thay_Linh_Automation_Hub_MOI_HOAN_TOAN_v1.3.2',
 'D:\Thay_Linh_Automation_Hub_MOI_HOAN_TOAN_v1.3.1',
 'D:\Thay_Linh_Automation_Hub',
 (Join-Path $env:USERPROFILE 'Desktop\Thay_Linh_Automation_Hub'),
 (Join-Path $env:LOCALAPPDATA 'ThayLinhAutomationHub')
)
foreach($r in $known){if($r -and (Test-Path -LiteralPath $r -PathType Container) -and -not $roots.Contains($r)){$roots.Add($r)}}
foreach($drive in @('D:\','C:\')){
 if(-not(Test-Path -LiteralPath $drive)){continue}
 try{Get-ChildItem -LiteralPath $drive -Directory -ErrorAction SilentlyContinue|Where-Object{$_.Name -match '(?i)(Thay.?Linh.*Automation.*Hub|Automation.*Hub)'}|Select-Object -First 10|ForEach-Object{if(-not $roots.Contains($_.FullName)){$roots.Add($_.FullName)}}}catch{}
}

$cmdNames=@('START_HUB.cmd','START_HUB.bat','start_hub.cmd','start_hub.bat','START_AUTOMATION_HUB.cmd','START_AUTOMATION_HUB.bat','start_server.cmd','start_server.bat','run_hub.cmd','run_hub.bat','start.cmd','run.cmd')
$psNames=@('START_HUB.ps1','start_hub.ps1','start_server.ps1','run_hub.ps1')
foreach($root in $roots){
 Log "Inspect Hub root: $root"
 foreach($name in $cmdNames){
  $f=Join-Path $root $name
  if(Test-Path -LiteralPath $f -PathType Leaf){ if(Start-Detached 'cmd.exe' @('/d','/c',$f) $root){if(Wait-Hub 12){Log "Hub recovered by $f";exit 0}} }
 }
 foreach($name in $psNames){
  $f=Join-Path $root $name
  if(Test-Path -LiteralPath $f -PathType Leaf){ if(Start-Detached 'powershell.exe' @('-NoProfile','-ExecutionPolicy','Bypass','-File',$f) $root){if(Wait-Hub 12){Log "Hub recovered by $f";exit 0}} }
 }
 $pkg=Join-Path $root 'package.json'
 if(Test-Path -LiteralPath $pkg){
  try{$p=Get-Content -LiteralPath $pkg -Raw|ConvertFrom-Json;$npm=Get-Command npm.cmd -ErrorAction SilentlyContinue;if($p.scripts.start -and $npm){if(Start-Detached $npm.Source @('start','--silent') $root){if(Wait-Hub 15){Log "Hub recovered by npm start in $root";exit 0}}}}catch{}
 }
}
Log 'Hub recovery exhausted safe candidates; 4310 remains unavailable.'
exit 1
