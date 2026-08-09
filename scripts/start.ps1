$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
docker compose up -d

$syncScript = Join-Path $PSScriptRoot "sync_vmnet_portproxy.ps1"
$powershellPath = (Get-Process -Id $PID).Path
$isAdministrator = ([Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)
$startArguments = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $syncScript,
    "-Watch"
)

if ($isAdministrator) {
    Start-Process -FilePath $powershellPath -ArgumentList $startArguments -WindowStyle Hidden
} else {
    Start-Process -FilePath $powershellPath -ArgumentList $startArguments -Verb RunAs -WindowStyle Hidden
}

Write-Host "Docker started; VMnet portproxy watcher started."
