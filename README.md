# Grid

> Working title — product name undecided.

Grid is a self-hosted, single-tenant, collaborative investigation platform — a modern
[Maltego](https://www.maltego.com/). Cases are infinite graph canvases of typed
entities (domains, IPs, emails, notes, …) connected by typed relationships, expanded
by transforms, with LLMs as first-class coworkers. Built by and for security people.
API-first: anything a human can do, automation and LLMs can do through the same path.

## Status

Early development. Phase 0 (scaffolding) is complete; Phase 1 (backend core: data
model, auth, CRUD, events) is next. See [docs/PLAN.md](docs/PLAN.md) for the roadmap
and [docs/JOURNAL.md](docs/JOURNAL.md) for session-by-session history.

## Stack

- **Backend** — Python 3.13, FastAPI, SQLAlchemy 2.0 + Alembic, Postgres 17 + pgvector,
  Temporal for background work. Tooling: uv, ruff, ty, pytest.
- **Frontend** — Vite, React 19, TypeScript strict, TanStack Router + Query, Zustand,
  React Flow, cmdk. Tooling: pnpm, Biome, Vitest, Playwright.
- **Infra** — Docker Compose (dev & small prod), Make for all tasks, GitHub Actions CI.

## Getting started

Requires: [uv](https://docs.astral.sh/uv/), Node 24+ with corepack (for pnpm), Docker
with the compose plugin, GNU Make.

```sh
make setup   # install backend (uv) + frontend (pnpm) deps — no Docker needed
make dev     # boot the full stack: Postgres, Temporal (+UI), API, worker, frontend
```

Then: frontend at http://localhost:5173, API at http://localhost:8000
(`/api/v1/healthz`), Temporal UI at http://localhost:8080. `make down` stops the stack.

Quality gates (same targets CI runs, no Docker required):

```sh
make test lint typecheck
```

Configuration is documented in [.env.example](.env.example); everything has dev-safe
defaults, so a fresh clone runs without any configuration.

## Documentation

| Doc | What it is |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design: deployment shape, data model, events, transforms, LLM layer |
| [docs/PLAN.md](docs/PLAN.md) | Phased build plan with exit criteria — the source of truth for what's next |
| [docs/DECISIONS.md](docs/DECISIONS.md) | ADR log — why things are the way they are |
| [docs/IDEAS.md](docs/IDEAS.md) | Running idea backlog (credited, dated) |
| [docs/JOURNAL.md](docs/JOURNAL.md) | Development journal, one entry per working session |
| [docs/notes/](docs/notes/) | Long-form notes, dissents, retrospectives |
| [CLAUDE.md](CLAUDE.md) | Working agreement for the implementer agents building this |

## Typeface note

The default theme uses Berkeley Mono, which is commercially licensed and not
redistributable — font files are gitignored and supplied locally per clone. The app
renders fine without them (falls back to `ui-monospace`).
