.PHONY: setup dev test e2e lint typecheck fmt api-client

setup:
	pnpm install

dev:
	pnpm dev --host

test:
	pnpm test

# Needs the real compose stack up (`make dev` from the repo root) — exercises
# the actual frontend + API + Postgres, not a standalone preview build.
e2e:
	pnpm e2e

lint:
	pnpm lint

typecheck:
	pnpm typecheck

fmt:
	pnpm fmt

api-client:
	pnpm exec openapi-ts
