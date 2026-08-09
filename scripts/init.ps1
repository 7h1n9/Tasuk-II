$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (!(Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
}

docker compose up -d mysql
Write-Host "Waiting for MySQL health check..."
Start-Sleep -Seconds 10
docker compose build
./scripts/start.ps1
