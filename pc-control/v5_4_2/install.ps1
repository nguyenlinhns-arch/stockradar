[CmdletBinding()]
param([switch]$NoStart)

$ErrorActionPreference='Stop'
$Version='5.4.2'
$PayloadCommit='758288012ae398491215651109d4bb1fe8dce208'
$RepoRaw="https://raw.githubusercontent.com/nguyenlinhns-arch/stockradar/$PayloadCommit/pc-control/v5_4_2"
$Expected=@{
 'agent.py'='22ed99b165093aff5a0c6023ddac63b58dc09c1d'
 'config.json'='4b2f56e33a53b3936f85de0c8939aa15596524e1'
 'repair_hub.ps1'='2b8f6ab59a7dfed52c6b00fe7a1b0c4a5314d4e5'
 'start_computer_use.ps1'='bd40137a46cacfa09397ca4369445b051da9aed0'
 'start_desktop_commander.ps1'='0fbf35259afcda9f295a7bcafc32dbba6cc6af05'
 'automation_hub.cmd'='af41efaebcf7b0cc75514ffae108c40afb955671'
 'uninstall.ps1'='c7d9384795b61b5110444ed9e410f5e4e8c62636'
}
$Root=Join-Path $env:LOCALAPPDATA 'ThayLinhPCBridge'
$LogDir=Join-Path $Root 'logs'
$TaskName='ThayLinh-PCBridge-V54'
$StartupDir=Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup'
$StartupCmd=Join-Path $StartupDir 'ThayLinh-PCBridge-V54.cmd'
$OpenAIComputerUse=Join-Path $env:USERPROFILE '.openai\computer-use'
$HubWrapper=Join-Path $OpenAIComputerUse 'automation_hub.cmd'
$InstallLog=Join-Path $env:TEMP 'ThayLinh-PCBridge-V542-install.log'

function Log([string]$Message){$line="$(Get-Date -Format o) $Message";Write-Host $line;Add-Content -LiteralPath $InstallLog -Value $line -Encoding UTF8}
function Download([string]$Name,[string]$Out){$url="$RepoRaw/$Name";Log "Download $url";Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $Out -TimeoutSec 30;if(-not(Test-Path -LiteralPath $Out)){throw "Download failed $Name"}}
function GitBlob([string]$Path){$b=[IO.File]::ReadAllBytes($Path);$h=[Text.Encoding]::ASCII.GetBytes(('blob '+$b.Length+[char]0));$all=New-Object byte[] ($h.Length+$b.Length);[Buffer]::BlockCopy($h,0,$all,0,$h.Length);[Buffer]::BlockCopy($b,0,$all,$h.Length,$b.Length);$sha=[Security.Cryptography.SHA1]::Create();try{return (($sha.ComputeHash($all)|ForEach-Object{$_.ToString('x2')})-join '')}finally{$sha.Dispose()}}
function AssertBlob([string]$Path,[string]$ExpectedSha){$a=GitBlob $Path;if($a -ne $ExpectedSha){throw "Integrity mismatch $Path expected=$ExpectedSha actual=$a"};Log "Integrity OK $([IO.Path]::GetFileName($Path)) $a"}
function ParsePS([string]$Path){$t=$null;$e=$null;[Management.Automation.Language.Parser]::ParseFile($Path,[ref]$t,[ref]$e)|Out-Null;if($e.Count){$e|ForEach-Object{Log "PARSE ERROR $($_.Message)"};throw "PowerShell parse failed $Path"};Log "PowerShell parse OK $Path"}
function Find-DriveBus {
 $c=New-Object System.Collections.Generic.List[string]
 $c.Add((Join-Path $env:USERPROFILE 'Google Drive\My Drive\07_CHATGPT_PC\PC_CONTROL_BUS'))
 $c.Add((Join-Path $env:USERPROFILE 'My Drive\07_CHATGPT_PC\PC_CONTROL_BUS'))
 Get-PSDrive -PSProvider FileSystem -ErrorAction SilentlyContinue|ForEach-Object{
  $r=$_.Root
  $c.Add((Join-Path $r 'My Drive\07_CHATGPT_PC\PC_CONTROL_BUS'))
  $c.Add((Join-Path $r '07_CHATGPT_PC\PC_CONTROL_BUS'))
  $c.Add((Join-Path $r 'Google Drive\My Drive\07_CHATGPT_PC\PC_CONTROL_BUS'))
 }
 return ($c|Where-Object{$_ -and (Test-Path -LiteralPath $_ -PathType Container)}|Select-Object -First 1)
}
function Write-DriveInstallStatus([hashtable]$Data){
 try{$bus=Find-DriveBus;if(-not $bus){Log 'Drive bus not visible locally yet.';return};$Data['time']=(Get-Date -Format o);$Data['version']=$Version;$json=$Data|ConvertTo-Json -Depth 8;Set-Content -LiteralPath (Join-Path $bus 'INSTALLER_STATUS.json') -Value $json -Encoding UTF8;Log "Drive installer readback written: $bus"}catch{Log "Drive readback failed: $($_.Exception.Message)"}
}

New-Item -ItemType Directory -Force -Path $Root,$LogDir,$StartupDir,$OpenAIComputerUse|Out-Null
Log "Upgrade/install ThayLinh PC Bridge $Version payload=$PayloadCommit"

# Stop V5.4.1/V5.4.2 bridge processes before replacing files.
try{
 Get-CimInstance Win32_Process|Where-Object{$_.ProcessId -ne $PID -and $_.CommandLine -and ($_.CommandLine -match '(?i)ThayLinhPCBridge.*agent\.py' -or $_.CommandLine -match '(?i)ThayLinhPCBridge.*run_bridge\.ps1')}|ForEach-Object{Log "Stopping old bridge PID $($_.ProcessId)";Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue}
 Start-Sleep -Seconds 2
}catch{Log "Old process cleanup warning: $($_.Exception.Message)"}

$temp=@{}
foreach($name in $Expected.Keys){$tmp=Join-Path $env:TEMP ("ThayLinh-V542-"+$name.Replace('/','_').Replace('\\','_')+'.tmp');Download $name $tmp;AssertBlob $tmp $Expected[$name];$temp[$name]=$tmp}
$python=Get-Command python.exe -ErrorAction SilentlyContinue;$py=Get-Command py.exe -ErrorAction SilentlyContinue
if($python){& $python.Source -m py_compile $temp['agent.py'];if($LASTEXITCODE){throw 'agent.py compile failed'}}elseif($py){& $py.Source -3 -m py_compile $temp['agent.py'];if($LASTEXITCODE){throw 'agent.py compile failed'}}else{throw 'Python 3 not found'}
Log 'Python compile OK.'
foreach($name in @('repair_hub.ps1','start_computer_use.ps1','start_desktop_commander.ps1','uninstall.ps1')){ParsePS $temp[$name]}

if(Test-Path -LiteralPath (Join-Path $Root 'config.json')){Copy-Item -Force -LiteralPath (Join-Path $Root 'config.json') -Destination (Join-Path $Root ("config.previous-"+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.json'))}
foreach($name in @('agent.py','config.json','repair_hub.ps1','start_computer_use.ps1','start_desktop_commander.ps1','automation_hub.cmd','uninstall.ps1')){Move-Item -Force -LiteralPath $temp[$name] -Destination (Join-Path $Root $name)}
Copy-Item -Force -LiteralPath (Join-Path $Root 'automation_hub.cmd') -Destination $HubWrapper

$runner=@'
$ErrorActionPreference='Continue'
$Root=Join-Path $env:LOCALAPPDATA 'ThayLinhPCBridge'
$Agent=Join-Path $Root 'agent.py'
$LogDir=Join-Path $Root 'logs'
New-Item -ItemType Directory -Force -Path $LogDir|Out-Null
$stdout=Join-Path $LogDir 'runner-out.log';$stderr=Join-Path $LogDir 'runner-err.log'
$env:THAYLINH_GITHUB_TOKEN='';$env:GH_TOKEN='';$env:GITHUB_TOKEN=''
while($true){
 try{$h=Invoke-RestMethod -Uri 'http://127.0.0.1:4321/health' -TimeoutSec 2;if($h.ok){Start-Sleep 5;continue}}catch{}
 $pythonw=Get-Command pythonw.exe -ErrorAction SilentlyContinue;$python=Get-Command python.exe -ErrorAction SilentlyContinue;$py=Get-Command py.exe -ErrorAction SilentlyContinue
 try{
  if($pythonw){$p=Start-Process -FilePath $pythonw.Source -ArgumentList @($Agent) -WorkingDirectory $Root -WindowStyle Hidden -PassThru;$p.WaitForExit()}
  elseif($python){$p=Start-Process -FilePath $python.Source -ArgumentList @($Agent) -WorkingDirectory $Root -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru;$p.WaitForExit()}
  elseif($py){$p=Start-Process -FilePath $py.Source -ArgumentList @('-3',$Agent) -WorkingDirectory $Root -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru;$p.WaitForExit()}
  else{exit 3}
 }catch{Add-Content -LiteralPath $stderr -Value "$(Get-Date -Format o) supervisor error $($_.Exception.Message)" -Encoding UTF8}
 Start-Sleep 3
}
'@
$runnerPath=Join-Path $Root 'run_bridge.ps1';Set-Content -LiteralPath $runnerPath -Value $runner -Encoding UTF8;ParsePS $runnerPath
$repair=@'
@echo off
start "ThayLinh PC Bridge" /min powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%LOCALAPPDATA%\ThayLinhPCBridge\run_bridge.ps1"
timeout /t 4 /nobreak >nul
powershell.exe -NoProfile -Command "try{Invoke-RestMethod 'http://127.0.0.1:4321/status' -TimeoutSec 5|ConvertTo-Json -Depth 8}catch{Write-Host $_.Exception.Message;exit 1}"
'@
Set-Content -LiteralPath (Join-Path $Root 'REPAIR_NOW.cmd') -Value $repair -Encoding ASCII
$startup=@'
@echo off
start "ThayLinh PC Bridge" /min powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%LOCALAPPDATA%\ThayLinhPCBridge\run_bridge.ps1"
'@
Set-Content -LiteralPath $StartupCmd -Value $startup -Encoding ASCII

$taskCreated=$false;$taskArgs="-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$runnerPath`""
try{$action=New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $taskArgs;$trigger=New-ScheduledTaskTrigger -AtLogOn;$settings=New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero);Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -RunLevel Limited -Force|Out-Null;$taskCreated=$true;Log "Scheduled task ready $TaskName"}catch{Log "ScheduledTask warning $($_.Exception.Message)";try{$taskCommand="powershell.exe $taskArgs";& schtasks.exe /Create /F /SC ONLOGON /TN $TaskName /TR $taskCommand /RL LIMITED|Out-Null;if($LASTEXITCODE -eq 0){$taskCreated=$true}}catch{}}
if($taskCreated){Remove-Item -Force -LiteralPath $StartupCmd -ErrorAction SilentlyContinue}else{Log 'Using Startup-folder fallback.'}

$marker=@{installed_version=$Version;payload_commit=$PayloadCommit;installed_at=(Get-Date -Format o);scheduled_task_created=$taskCreated;drive_bus_mode='private-drivefs';payload_git_blobs=$Expected}|ConvertTo-Json -Depth 6
Set-Content -LiteralPath (Join-Path $Root 'install_state.json') -Value $marker -Encoding UTF8

$summary=@{ok=$true;phase='installed';task_created=$taskCreated;bridge_health=$false;hub_ok=$false;computer_use_ok=$false;drive_bus_visible=[bool](Find-DriveBus)}
if(-not $NoStart){
 Log 'Starting Hub/Computer Use recovery.'
 & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Root 'repair_hub.ps1')
 & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Root 'start_computer_use.ps1')
 Log 'Starting V5.4.2 supervisor.'
 Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-WindowStyle','Hidden','-File',$runnerPath) -WindowStyle Hidden
 Start-Sleep -Seconds 6
 try{$h=Invoke-RestMethod -Uri 'http://127.0.0.1:4321/health' -TimeoutSec 5;$summary.bridge_health=[bool]$h.ok;Log ("Bridge health "+($h|ConvertTo-Json -Compress))}catch{Log "Bridge health unavailable $($_.Exception.Message)"}
 try{$r=Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:4310/' -TimeoutSec 4;$summary.hub_ok=($r.StatusCode -ge 200 -and $r.StatusCode -lt 500)}catch{}
 foreach($u in @('http://127.0.0.1:8777/health','http://127.0.0.1:8766/health')){try{$r=Invoke-WebRequest -UseBasicParsing -Uri $u -TimeoutSec 3;if($r.StatusCode -lt 500){$summary.computer_use_ok=$true;break}}catch{}}
}
Write-DriveInstallStatus $summary
Log 'V5.4.2 install/upgrade completed.'
Write-Host "Installed: $Root"
Write-Host 'Private Drive bus: 07_CHATGPT_PC\PC_CONTROL_BUS'
Write-Host 'Bridge: http://127.0.0.1:4321/'
