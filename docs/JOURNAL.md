# Development Journal

Append-only, newest entry at the top. Every working session gets an entry: what
happened, what surprised you, what's next. Write for the teammate who wasn't there.

---

## 2026-07-23 — Phase 0: scaffolding & tooling

Built out Phase 0 in full: `backend/` (uv, Python 3.13, FastAPI + `/api/v1/healthz`,
ruff + ty, pytest), `frontend/` (Vite + React 19 + TS strict, Biome, Vitest, a
placeholder page that fetches healthz through the Vite dev proxy), `deploy/compose.dev.yaml`
(db as `pgvector/pgvector:pg17`, `temporal` auto-setup sharing that same Postgres,
`temporal-ui`, `api`, a `worker` placeholder entrypoint that idles until Phase 3, and
`frontend`), root/backend/frontend Makefiles, GitHub Actions CI, `.gitignore` +
`.editorconfig`, and the CLAUDE.md Commands section.

Verified for real, not just written: built every Docker image, ran
`docker compose -f deploy/compose.dev.yaml up -d`, and curled healthz through both the
API directly and the frontend's dev proxy, hit the Temporal UI (200 OK), and confirmed
the worker container logs its idle message. `make setup && make test lint typecheck`
all pass natively (no Docker) for both stacks — that's also what CI runs, on plain
GitHub-hosted runners with `astral-sh/setup-uv` + `pnpm/action-setup`, no
Docker-in-Docker needed since Docker is only for `make dev`.

Surprises / notes for next session:
- **Docker required a workaround this session**: gradius added the sandbox user to the
  `docker` group mid-session, but group membership doesn't take effect without a new
  login session, so every docker command needed `sg docker -c "..."`. Plain `docker`
  should work directly in a fresh shell/session from now on — try that first before
  reaching for `sg docker -c`.
- **pnpm 11's default supply-chain policy broke the frontend Docker build**: without a
  pinned version, `corepack` fetched pnpm 11.16.0 inside the image, which rejected
  `postcss` for being "too recently published" (`minimumReleaseAge`). Fixed by pinning
  `packageManager` in `frontend/package.json` to `pnpm@10.34.5` (via `corepack use`) so
  Docker and local installs use the same, older, unaffected version. Worth revisiting
  once the ecosystem settles — don't just bump to pnpm@latest without checking this.
- **vitest 2.x doesn't support Vite 8** (the current `create-vite` scaffold defaults
  to Vite 8, but vitest 2.x's bundled Vite peer type surface is v5-shaped and its
  plugin types don't line up, which `tsc -b` catches). Bumped to `vitest@^4.1.10`,
  which does support it.
- The default `create-vite` React 19 template now ships `oxlint`, not eslint — swapped
  for Biome per the stack decision; removed the oxlint config and its dependency.
- Full theming (CSS-variable tokens, Berkeley Mono, industrial look) is explicitly
  Phase 2 scope — the Phase 0 frontend page uses bare unstyled CSS with the fallback
  mono stack on purpose, not a placeholder for something forgotten.

Next: Phase 1 — backend core (data model, auth, CRUD, events). First unchecked box is
"Settings via pydantic-settings; SQLAlchemy 2.0 typed models; Alembic baseline."

## 2026-07-23 — Planning session (gradius + architect model)

Founded the project. Product brief: modern Maltego — collaborative graph investigation
platform, single-tenant stacks, LLMs as first-class coworkers, API-first, transforms
as the extension model.

Decisions made (details in DECISIONS.md): Postgres over DuckDB (ADR-002), SQLAlchemy +
Alembic (ADR-003), Temporal from day 1 (ADR-004), React Flow behind a renderer
abstraction targeting 1–2k nodes (ADR-005), server-authoritative event-log sync — no
CRDTs (ADR-006), transform trust boundary at HTTP with a serverless-shaped spec
(ADR-007), pydantic-ai provisionally (ADR-008), sessions + API keys with service-layer
RBAC (ADR-009).

Wrote ARCHITECTURE.md, PLAN.md (phases 0–6 + backlog), seeded IDEAS.md, and CLAUDE.md
for implementer agents. Added `docs/notes/` as long-form thinking space for everyone,
agents explicitly included. gradius dropped the Berkeley Mono woff2 set into
`berkeley-mono-web/` — it's the default theme typeface (self-hosted, commercial
license, not redistributable). gradius is setting up the dev environment. Next:
Phase 0.
