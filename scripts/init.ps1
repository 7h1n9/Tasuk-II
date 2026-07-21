$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (!(Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
}

docker compose up -d mysql
Write-Host "等待 MySQL 健康检查通过..."
Start-Sleep -Seconds 10
docker compose build
docker compose up -d backend frontend

