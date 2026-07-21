SHELL := pwsh

.PHONY: init start stop reset build backend frontend smoke

init:
	./scripts/init.ps1

start:
	./scripts/start.ps1

stop:
	./scripts/stop.ps1

reset:
	./scripts/reset_all.ps1

build:
	docker compose build

backend:
	docker compose up -d backend

frontend:
	docker compose up -d frontend

smoke:
	python scripts/smoke_test.py

