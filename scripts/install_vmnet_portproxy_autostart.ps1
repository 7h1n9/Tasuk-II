param(
    [switch]$Uninstall
)

$ErrorActionPreference = "Stop"
$taskName = "CTF-Agent-Range-VMnet-Portproxy"
$watcher = Join-Path $PSScriptRoot "sync_vmnet_portproxy.ps1"

function Test-IsAdministrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-IsAdministrator)) {
    $powershellPath = (Get-Process -Id $PID).Path
    $arguments = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $PSCommandPath
    )
    if ($Uninstall) {
        $arguments += "-Uninstall"
    }
    Start-Process -FilePath $powershellPath -ArgumentList $arguments -Verb RunAs -Wait
    exit $LASTEXITCODE
}

if ($Uninstall) {
    Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -like "*sync_vmnet_portproxy.ps1*" } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $taskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $watcher)) {
    throw "Watcher script not found: $watcher"
}

$currentUser = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$powershellPath = (Get-Process -Id $PID).Path
$actionArguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$watcher`" -Watch"
$action = New-ScheduledTaskAction -Execute $powershellPath -Argument $actionArguments
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $currentUser -RandomDelay (New-TimeSpan -Seconds 30)
$principal = New-ScheduledTaskPrincipal -UserId $currentUser -LogonType Interactive -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew

Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like "*sync_vmnet_portproxy.ps1*" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Force | Out-Null

Start-ScheduledTask -TaskName $taskName
Write-Host "Installed and started scheduled task: $taskName"
