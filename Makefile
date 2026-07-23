# --project-directory makes compose read .env from the repo root (default would be deploy/)
COMPOSE = docker compose -f deploy/compose.dev.yaml --project-directory .

.PHONY: setup dev down test lint typecheck fmt migrate api-client

setup:
	$(MAKE) -C backend setup
	$(MAKE) -C frontend setup

dev:
	$(COMPOSE) up --build

down:
	$(COMPOSE) down

test:
	$(MAKE) -C backend test
	$(MAKE) -C frontend test

lint:
	$(MAKE) -C backend lint
	$(MAKE) -C frontend lint

typecheck:
	$(MAKE) -C backend typecheck
	$(MAKE) -C frontend typecheck

fmt:
	$(MAKE) -C backend fmt
	$(MAKE) -C frontend fmt

migrate:
	$(MAKE) -C backend migrate

api-client:
	$(MAKE) -C backend openapi-schema
	$(MAKE) -C frontend api-client
