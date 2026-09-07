[CmdletBinding()]
param([switch]$NoStart)

$ErrorActionPreference = 'Stop'
$Version = '5.4.1'
$PayloadCommit = '4ae0a3bc6f5ff0acba95e4630c41c09161e8bc9f'
$RepoRaw = "https://raw.githubusercontent.com/nguyenlinhns-arch/stockradar/$PayloadCommit/pc-control/v5_4"
$Expected = @{
    'agent.py' = '038d2c7868b19107f798c1cf11447c99683c51e3'
    'config.json' = '4e191a55d142672b4ea2a80944d3520cf4d130eb'
    'repair_hub.ps1' = 'bd28ba1bf6a947ef885a740195e9eadb750bd1d3'
    'automation_hub.cmd' = 'af41efaebcf7b0cc75514ffae108c40afb955671'
    'start_desktop_commander.ps1' = 'de93a97b3fec0f12fe7f7a6e69e55be440f15500'
}

$Root = Join-Path $env:LOCALAPPDATA 'ThayLinhPCBridge'
$LogDir = Join-Path $Root 'logs'
$TaskName = 'ThayLinh-PCBridge-V54'
$StartupDir = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup'
$StartupCmd = Join-Path $StartupDir 'ThayLinh-PCBridge-V54.cmd'
$OpenAIComputerUse = Join-Path $env:USERPROFILE '.openai\computer-use'
$HubWrapper = Join-Path $OpenAIComputerUse 'automation_hub.cmd'
$InstallLog = Join-Path $env:TEMP 'ThayLinh-PCBridge-V54-install.log'

function Log([string]$Message) {
    $line = "$(Get-Date -Format o) $Message"
    Write-Host $line
    Add-Content -LiteralPath $InstallLog -Value $line -Encoding UTF8
}

function Download([string]$Name, [string]$OutFile) {
    $url = "$RepoRaw/$Name"
    Log "Download $url"
    Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $OutFile -TimeoutSec 30
    if (-not (Test-Path -LiteralPath $OutFile)) { throw "Download failed: $url" }
    if ((Get-Item -LiteralPath $OutFile).Length -lt 10) { throw "Downloaded file too small: $Name" }
}

function GitBlobSha1([string]$Path) {
    $bytes = [System.IO.File]::ReadAllBytes($Path)
    $header = [System.Text.Encoding]::ASCII.GetBytes(('blob ' + $bytes.Length + [char]0))
    $all = New-Object byte[] ($header.Length + $bytes.Length)
    [System.Buffer]::BlockCopy($header, 0, $all, 0, $header.Length)
    [System.Buffer]::BlockCopy($bytes, 0, $all, $header.Length, $bytes.Length)
    $sha1 = [System.Security.Cryptography.SHA1]::Create()
    try { return (($sha1.ComputeHash($all) | ForEach-Object { $_.ToString('x2') }) -join '') }
    finally { $sha1.Dispose() }
}

function AssertBlob([string]$Path, [string]$ExpectedSha) {
    $actual = GitBlobSha1 $Path
    if ($actual -ne $ExpectedSha) { throw "Integrity mismatch for $Path. Expected $ExpectedSha got $actual" }
    Log "Integrity OK: $([System.IO.Path]::GetFileName($Path)) $actual"
}

function ParsePowerShell([string]$Path) {
    $tokens = $null
    $errors = $null
    [System.Management.Automation.Language.Parser]::ParseFile($Path, [ref]$tokens, [ref]$errors) | Out-Null
    if ($errors.Count -gt 0) {
        $errors | ForEach-Object { Log "PARSE ERROR $Path : $($_.Message)" }
        throw "PowerShell parse failed: $Path"
    }
    Log "PowerShell parse OK: $Path"
}

New-Item -ItemType Directory -Force -Path $Root, $LogDir, $StartupDir, $OpenAIComputerUse | Out-Null
Log "Installing ThayLinh PC Bridge v$Version payload=$PayloadCommit into $Root"

$tempFiles = @{}
foreach ($name in $Expected.Keys) {
    $tmp = Join-Path $env:TEMP ("ThayLinh-V54-" + $name.Replace('\','_').Replace('/','_') + '.tmp')
    Download $name $tmp
    AssertBlob $tmp $Expected[$name]
    $tempFiles[$name] = $tmp
}

$python = Get-Command python.exe -ErrorAction SilentlyContinue
$py = Get-Command py.exe -ErrorAction SilentlyContinue
if ($python) {
    & $python.Source -m py_compile $tempFiles['agent.py']
    if ($LASTEXITCODE -ne 0) { throw 'agent.py failed Python syntax check' }
} elseif ($py) {
    & $py.Source -3 -m py_compile $tempFiles['agent.py']
    if ($LASTEXITCODE -ne 0) { throw 'agent.py failed Python syntax check' }
} else {
    throw 'Python 3 not found. Repair the existing Computer Use/Automation Hub Python installation first.'
}
Log 'Python syntax check OK.'
ParsePowerShell $tempFiles['repair_hub.ps1']
ParsePowerShell $tempFiles['start_desktop_commander.ps1']

$existingConfig = Join-Path $Root 'config.json'
if (Test-Path -LiteralPath $existingConfig) {
    $backup = Join-Path $Root ("config.previous-" + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.json')
    Copy-Item -Force -LiteralPath $existingConfig -Destination $backup
    Log "Previous config backed up: $backup"
}

Move-Item -Force -LiteralPath $tempFiles['agent.py'] -Destination (Join-Path $Root 'agent.py')
Move-Item -Force -LiteralPath $tempFiles['config.json'] -Destination $existingConfig
Move-Item -Force -LiteralPath $tempFiles['repair_hub.ps1'] -Destination (Join-Path $Root 'repair_hub.ps1')
Move-Item -Force -LiteralPath $tempFiles['start_desktop_commander.ps1'] -Destination (Join-Path $Root 'start_desktop_commander.ps1')
Copy-Item -Force -LiteralPath $tempFiles['automation_hub.cmd'] -Destination (Join-Path $Root 'automation_hub.cmd')
Move-Item -Force -LiteralPath $tempFiles['automation_hub.cmd'] -Destination $HubWrapper
Log "Hub recovery wrapper installed: $HubWrapper"

$runner = @'
$ErrorActionPreference = 'Continue'
$Root = Join-Path $env:LOCALAPPDATA 'ThayLinhPCBridge'
$Agent = Join-Path $Root 'agent.py'
$LogDir = Join-Path $Root 'logs'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$stdout = Join-Path $LogDir 'runner-out.log'
$stderr = Join-Path $LogDir 'runner-err.log'
if (-not (Test-Path -LiteralPath $Agent)) { exit 2 }

while ($true) {
    try {
        $health = Invoke-RestMethod -Uri 'http://127.0.0.1:4321/health' -TimeoutSec 2
        if ($health.ok) { Start-Sleep -Seconds 10; continue }
    } catch {}

    $pythonw = Get-Command pythonw.exe -ErrorAction SilentlyContinue
    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    $py = Get-Command py.exe -ErrorAction SilentlyContinue
    try {
        if ($pythonw) {
            $p = Start-Process -FilePath $pythonw.Source -ArgumentList @($Agent) -WorkingDirectory $Root -WindowStyle Hidden -PassThru
            $p.WaitForExit()
        } elseif ($python) {
            $p = Start-Process -FilePath $python.Source -ArgumentList @($Agent) -WorkingDirectory $Root -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
            $p.WaitForExit()
        } elseif ($py) {
            $p = Start-Process -FilePath $py.Source -ArgumentList @('-3',$Agent) -WorkingDirectory $Root -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
            $p.WaitForExit()
        } else { exit 3 }
    } catch {
        Add-Content -LiteralPath $stderr -Value "$(Get-Date -Format o) supervisor error: $($_.Exception.Message)" -Encoding UTF8
    }
    Start-Sleep -Seconds 5
}
'@
$runnerPath = Join-Path $Root 'run_bridge.ps1'
Set-Content -LiteralPath $runnerPath -Value $runner -Encoding UTF8
ParsePowerShell $runnerPath

$repair = @'
@echo off
setlocal
start "ThayLinh PC Bridge" /min powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%LOCALAPPDATA%\ThayLinhPCBridge\run_bridge.ps1"
timeout /t 4 /nobreak >nul
powershell.exe -NoProfile -Command "try { (Invoke-RestMethod -Uri 'http://127.0.0.1:4321/status' -TimeoutSec 5) | ConvertTo-Json -Depth 8 } catch { Write-Host $_.Exception.Message; exit 1 }"
endlocal
'@
Set-Content -LiteralPath (Join-Path $Root 'REPAIR_NOW.cmd') -Value $repair -Encoding ASCII

$startup = @'
@echo off
start "ThayLinh PC Bridge" /min powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%LOCALAPPDATA%\ThayLinhPCBridge\run_bridge.ps1"
'@
Set-Content -LiteralPath $StartupCmd -Value $startup -Encoding ASCII

$taskCreated = $false
$taskArgs = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$runnerPath`""
try {
    $action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $taskArgs
    $trigger = New-ScheduledTaskTrigger -AtLogOn
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero)
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -RunLevel Limited -Force | Out-Null
    $taskCreated = $true
    Log "Scheduled task created with restart policy: $TaskName"
} catch {
    Log "Register-ScheduledTask failed: $($_.Exception.Message)"
    try {
        $taskCommand = "powershell.exe $taskArgs"
        & schtasks.exe /Create /F /SC ONLOGON /TN $TaskName /TR $taskCommand /RL LIMITED | Out-Null
        if ($LASTEXITCODE -eq 0) { $taskCreated = $true; Log "schtasks fallback created: $TaskName" }
    } catch { Log "schtasks fallback failed: $($_.Exception.Message)" }
}

if ($taskCreated) { Remove-Item -Force -LiteralPath $StartupCmd -ErrorAction SilentlyContinue }
else { Log 'Scheduled task unavailable; Startup-folder fallback remains active.' }

$marker = @{
    installed_version = $Version
    payload_commit = $PayloadCommit
    installed_at = (Get-Date -Format o)
    install_root = $Root
    scheduled_task_created = $taskCreated
    hub_wrapper = $HubWrapper
    payload_git_blobs = $Expected
} | ConvertTo-Json -Depth 6
Set-Content -LiteralPath (Join-Path $Root 'install_state.json') -Value $marker -Encoding UTF8

if (-not $NoStart) {
    Log 'Running Hub autodiscovery once.'
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Root 'repair_hub.ps1')
    Log 'Starting bridge supervisor.'
    Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-WindowStyle','Hidden','-File',$runnerPath) -WindowStyle Hidden
    Start-Sleep -Seconds 5
    try {
        $health = Invoke-RestMethod -Uri 'http://127.0.0.1:4321/health' -TimeoutSec 5
        Log ("Bridge health OK: " + ($health | ConvertTo-Json -Compress))
    } catch { Log "Bridge health unavailable: $($_.Exception.Message)" }
    try {
        $hub = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:4310/' -TimeoutSec 5
        Log "Hub root HTTP $($hub.StatusCode)"
    } catch { Log "Hub root unavailable: $($_.Exception.Message)" }
}

Log 'Install completed.'
Write-Host "`nInstalled: $Root"
Write-Host 'Bridge health: http://127.0.0.1:4321/health'
Write-Host 'Bridge status: http://127.0.0.1:4321/status'
Write-Host 'Hub: http://127.0.0.1:4310/'
Write-Host "Manual repair: $Root\REPAIR_NOW.cmd"
