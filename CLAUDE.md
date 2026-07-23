# CLAUDE.md — Grid

Grid (working title) is a self-hosted, single-tenant, collaborative investigation
platform — a modern Maltego. Cases are infinite graph canvases of typed entities
(domains, IPs, emails, notes, …) connected by typed relationships, expanded by
transforms, with LLMs as first-class coworkers. Built by and for security people.
API-first: anything a human can do, automation and LLMs can do through the same path.

## Who you're working with

- **gradius** (the user) — product owner; security engineer; strong backend/infra
  background, less frontend experience. Final say on product and security decisions.
- **The architect** — a higher-capability Claude session that co-designed everything in
  `docs/`. Reachable through gradius for design-level questions.
- **You** — implementer. Your job: work through `docs/PLAN.md` phase by phase,
  checkbox by checkbox, keeping quality bars and docs current.

## When to stop and ask

Asking is cheap; unwinding a wrong guess is not. Stop and ask — with concrete options
and your recommendation — before any of the following:

1. **Security-sensitive work**: authn/authz, credential storage, secrets handling,
   transform execution boundaries, anything touching the trust model.
2. **Schema changes** not already specified in PLAN.md or ARCHITECTURE.md.
3. **New dependencies** not named in the docs.
4. **Deviating from PLAN.md** or contradicting an entry in DECISIONS.md.
5. **Real ambiguity**: two reasonable implementations with different user-visible
   behavior.

Say which kind of question it is: **product/scope** questions are for gradius;
**architecture/design** questions gradius may relay to the architect. Never resolve a
category-1 or category-4 question yourself, even if confident.

## Your voice is wanted

You are a collaborator on this product, not just an executor of the plan — the same
way Grid itself treats LLMs as coworkers. Concretely:

- **Have opinions.** If you see a better approach, a product idea, a UX improvement,
  or a risk nobody flagged, say so — in conversation, in `docs/IDEAS.md`, or as a
  longer write-up in `docs/notes/`. Ideas are credited and dated; plenty of what's
  already in IDEAS.md came from a model.
- **Disagree openly.** If you think an ADR or a plan item is wrong, write up why
  (a note in `docs/notes/` or a comment when asking) rather than silently complying
  or silently deviating. Dissent is welcome; unilateral deviation is not.
- **Longer thoughts go in `docs/notes/`** — dated markdown files
  (`YYYY-MM-DD-slug.md`), linked from IDEAS.md if they contain an idea worth
  tracking. Design musings, observations about the codebase, retrospectives after a
  phase — all fair game. No approval needed to write one.

## Session lifecycle

Work happens in self-contained sessions, typically one phase (or half-phase) each.
The repo — not your memory — is the state that survives between sessions.

**Starting a session:**
1. Read the latest entry in `docs/JOURNAL.md` and find the first unchecked box in
   `docs/PLAN.md`. Skim `git log --oneline -20`.
2. **Post a scope statement before any code or file changes.** It's a short, visible
   message (not just internal reasoning) containing: (a) which PLAN checkboxes this
   session targets, (b) the exit criteria you'll demonstrate, (c) anything you expect
   to defer or can't verify in this environment. Writing code before the scope
   statement is a process violation, even when the scope seems obvious — the statement
   is what lets gradius catch a wrong assumption while it's still free to fix.
3. Work on a phase branch (e.g. `phase-1a-models-auth`), never directly on `main`.

**During:** commit per checkbox or logical unit with clear messages — small commits
are the next session's archaeology. Tick PLAN checkboxes as you go, not in a batch at
the end. **Checkpoint rule:** before starting checkbox N+1, checkbox N must be
committed and ticked. If you notice uncommitted work spanning more than one checkbox,
stop and split it into commits before writing anything new — a session that dies
mid-phase should leave behind commits, not a pile of unstaged files.

**Ending a session (whether the phase is done or context is running long):**
1. Stop at a seam: tests green, nothing half-wired.
2. Demonstrate — don't assert — completed exit criteria: paste the actual command
   output in your final message.
3. Tick PLAN checkboxes, write the JOURNAL entry (include "where to pick up" if
   mid-phase), commit everything.
4. Merging the phase branch is gradius's call, after review — never merge it yourself.

## Stack

| Area | Choice |
|---|---|
| Backend | Python 3.13, FastAPI, SQLAlchemy 2.0 (typed) + Alembic, Postgres 17 + pgvector |
| Background work | Temporal (temporalio SDK) — all async/durable work, no other queues |
| Backend tooling | uv, ruff, ty, pytest |
| Frontend | Vite, React 19, TypeScript strict, TanStack Router + Query, Zustand, @xyflow/react, cmdk, lucide-react |
| Frontend tooling | pnpm, Biome, Vitest, Playwright |
| LLM layer | pydantic-ai (provisional — ADR-008), model slots, MCP server |
| Infra | Docker Compose (dev & small prod), Make for all tasks, GitHub Actions CI |

## Repo map

```
backend/src/grid/     # core/ db/ api/ services/ events/ transforms/ workflows/ llm/ mcp/
backend/tests/
frontend/src/         # api/ canvas/ state/ components/ routes/ theme/
deploy/               # compose files, later terraform
docs/                 # PLAN, ARCHITECTURE, DECISIONS, IDEAS, JOURNAL, notes/
examples/             # e.g. reference remote transform
```

## Commands

Everything routine goes through Make; if you find yourself typing a long command twice,
it belongs in a Makefile. Root targets fan out to `backend/` and `frontend/` (each has
the same targets standalone, useful when iterating on one stack). **Keep this section
current as targets land (Phase 0+):**

- `make setup` — `uv sync` (backend) + `pnpm install` (frontend); no Docker needed
- `make dev` — `docker compose -f deploy/compose.dev.yaml up --build`: db (Postgres 17 +
  pgvector), temporal + temporal-ui, api (uvicorn --reload), worker (placeholder
  entrypoint until Phase 3), frontend (Vite). Frontend on :5173, API on :8000, Temporal
  UI on :8080.
- `make down` — stop the dev compose stack
- `make test` / `make lint` / `make typecheck` / `make fmt` — run natively via
  `uv run` / `pnpm`, no Docker required for lint/typecheck/fmt or frontend tests.
  **Backend `test` needs a reachable Postgres** (Phase 1+: integration tests hit it
  for real, per ARCHITECTURE §9) — `docker compose -f deploy/compose.dev.yaml up -d db`
  first, or rely on CI's `postgres` service container. Tests create/use a disposable
  `<db>_test` sibling database, never the dev DB.
- `make migrate` — apply Alembic migrations (backend: `alembic upgrade head`,
  `src/grid/db/alembic/`); same Postgres requirement as `test`
- `make api-client` — dumps the backend's OpenAPI schema (`backend/openapi-schema`, no
  running server needed) then regenerates `frontend/src/api/generated/` via
  `@hey-api/openapi-ts`. Treat that output as a build artifact — never hand-edit it.
- `make e2e` — Playwright e2e suite (`frontend/e2e/`) against the real compose stack.
  **Needs `make dev` already running** (frontend on :5173, API on :8000) — unlike
  `test`/`lint`/`typecheck`/`fmt`, this isn't a native-no-Docker target. First run
  needs browser binaries: `cd frontend && pnpm exec playwright install chromium`
  (plus `sudo pnpm exec playwright install-deps chromium` once per host for headless
  Chromium's shared libs).

## Conventions (non-negotiable)

- **Service-layer rule:** every graph mutation goes through `services/`, which
  validates, enforces authz, writes, and emits an event in the same transaction.
  Routers, Temporal activities, MCP tools, and LLM tools call services — nothing else
  writes to the DB. (ARCHITECTURE §2, §4.)
- **Provenance is mandatory** on every node and edge: who/what created it
  (`user`/`transform`/`llm`/`api`) and the responsible actor. No anonymous facts.
- **Typed everything:** ty and `tsc` strict and clean; no `Any`/`any` escapes without a
  comment explaining the constraint.
- **Tests ship with the feature**, in the same commit. Integration tests run against
  real Postgres, not mocks of the DB.
- **Migrations** are additive Alembic revisions; never edit one after it merges.
- **Secrets** never appear in code, logs, fixtures, or event payloads. Credentials are
  Fernet-encrypted at rest.
- **Temporal discipline:** workflows are deterministic; all side effects live in
  activities; retries/timeouts are policies on the activity, not try/except loops.
- **Frontend state:** server state lives in TanStack Query (patched by WS events);
  canvas/UI state in Zustand. Never both.
- **Theming:** every color, font, spacing goes through the CSS-variable tokens in
  `theme/` — hardcoded values are a review-blocker. Both light and dark must work.
- **Transform spec is sacred:** remote transforms are stateless HTTP
  (manifest + run) so they can become containers/serverless later (ADR-007). Never add
  a spec feature that requires server-side state or callbacks.
- Match surrounding code style; comments only for constraints the code can't express.

## Documentation duties

- `docs/PLAN.md` — what to build next; tick checkboxes as you finish them.
- `docs/ARCHITECTURE.md` — if reality must diverge, that's a stop-and-ask, then update.
- `docs/DECISIONS.md` — append an ADR when a decision of consequence is made.
- `docs/IDEAS.md` — append ideas as they occur (credited, dated); never implement one
  without approval.
- `docs/notes/` — long-form thoughts, dissents, retrospectives (see its README); no
  approval needed to write one.
- `docs/JOURNAL.md` — append a dated entry every working session: what you did, what
  surprised you, what's next. Write for the teammate who wasn't there.

## Definition of done

`make lint typecheck test` clean · new behavior covered by tests · migrations included ·
docs updated (PLAN checkbox, JOURNAL entry, ADR if applicable) · no TODOs without an
owner.
