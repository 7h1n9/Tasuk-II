#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  cp .env.example .env
fi

docker compose up -d mysql
sleep 10
docker compose build
docker compose up -d backend frontend

