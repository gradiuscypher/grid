# Development Journal

Append-only, newest entry at the top. Every working session gets an entry: what
happened, what surprised you, what's next. Write for the teammate who wasn't there.

---

## 2026-07-23 — Phase 1b: CRUD, event log/WS, OpenAPI client, authz matrix — Phase 1 complete

Picked up right where 1a left off, on `phase-1b-crud-events` (stacked on
`phase-1a-models-auth`, which was still awaiting review — opened PR #2 for it
at the start of this session; per gradius's call, I open PRs and they merge,
never the reverse). Finished all four remaining Phase 1 checkboxes in one
session, committing after each.

**Landed:**
- Full service-layer CRUD for nodes, edges, notes, waypoints, groups, plus
  filling out cases (update/delete). Nodes/edges are dedup-idempotent on
  create (repeat create with the same canonical value returns the existing
  row, matching ARCHITECTURE's "dedup is structural"); canonicalization rules
  per builtin entity type live in `services/canonicalize.py`. Node/edge
  identity fields (entity_type, value) are immutable after creation. Deleting
  a node cascades its edges and group memberships by hand in the service
  layer — the DB has no FK cascade anywhere, by design (service layer is the
  only writer), so `delete_case` also manually clears every child table in
  FK-safe order.
- Event log + realtime: every mutation across all these services now appends
  a typed event row and queues a `pg_notify` in the same transaction
  (`events/service.py`). A background task (`events/listener.py`, started in
  `main.py`'s new lifespan) holds one LISTEN connection per process and fans
  notified rows out to in-process WS subscribers (`events/manager.py`).
  `/ws/cases/{id}` replays the backlog since a client-supplied `seq`, then
  streams live.
- **WS auth needed a real decision, not just an implementation.** ARCHITECTURE
  doesn't cover it, and the existing cookie+custom-header pattern doesn't
  carry over — browsers can't attach a custom header to a WS handshake. Asked
  gradius; went with short-lived, single-use REST-minted tickets
  (`POST /api/v1/ws-tickets`, `events/tickets.py`) over Origin-header
  validation. In-memory by design, matching the single-API-process compose
  topology — would need to move to Postgres if the API ever runs multiple
  replicas.
- OpenAPI polish: every route now has an explicit `operation_id` (previously
  FastAPI's verbose auto-generated ones). `make api-client` does real work
  now — `backend openapi-schema` dumps `app.openapi()` without needing a
  running server, `@hey-api/openapi-ts` generates a typed fetch client into
  `frontend/src/api/generated/` (committed; the intermediate `openapi.json`
  dump is gitignored and regenerated each run).
- Comprehensive role×action authz matrix test
  (`tests/api/test_authz_matrix.py`): for every case-scoped action, checks
  that the role just below its documented minimum is forbidden and the
  minimum role itself succeeds. 75 backend tests total now, all real
  Postgres.

**Surprises / notes for next session:**
- **The live-broadcast path can't be exercised by the existing pytest
  harness**, and that took real debugging time to nail down (not a code bug —
  I initially thought the LISTEN/NOTIFY pipeline itself was broken, added
  debug tracing, and eventually proved via a manual dev-stack walkthrough that
  it works correctly end-to-end). The per-test transaction fixture never
  truly commits (rolled back at teardown), so `pg_notify` never actually
  fires; and mixing httpx's async client with Starlette's thread-portal WS
  test client risks binding a DB connection to the wrong event loop. Automated
  coverage here is ticket issue/redeem/expiry and the `/ws-tickets` REST
  endpoint; live broadcast is verified manually against the dev compose stack
  (transcript below) — flagging this gap explicitly rather than leaving it
  silently under-tested. Worth reconsidering if `httpx-ws` (or similar) is
  ever added as a dependency.
- `@hey-api/client-fetch` is deprecated as a standalone package — bundled
  directly into `@hey-api/openapi-ts` now. Reference it by plugin name in
  `openapi-ts.config.ts`, don't install it separately (I did, then removed it
  once `pnpm add` warned about it).
- Two pre-existing tests (`test_models.py`, `test_entity_types.py`) created
  their own ad hoc `EntityType(name="domain", ...)` rows for fixtures; once
  `conftest.py` started seeding the real ARCHITECTURE §3 builtins (needed so
  my new tests could reference "domain"/"ipv4" by name like production code
  does), those collided on the unique name constraint. Renamed to
  `test_widget`, a name that can't collide with real builtins.
- Still open from 1a, unchanged: API key scope is a single `read_only: bool`,
  and there's no admin/superuser concept gating entity-type management.
  Neither came up as blocking this session; still flagging for the architect.

**Exit criteria demonstrated** (curl + WS transcript, not just asserted):
register → create case → mint API key → create a domain node → **repeat
create with different casing returns HTTP 200 with the same node id** (dedup)
→ create an IPv4 node → connect a second WS client with a minted ticket, which
immediately replays the case/node backlog → from a separate terminal, create
an edge and a third node → **the live WS client receives `edge.created` and
`node.created` events in real time**, no polling. `test_authz_matrix.py`'s 13
tests pass (role×action boundaries for cases/nodes/edges/notes/waypoints/
groups). `make api-client` generates a clean TypeScript client from a cold
start (deleted `openapi.json` and `src/api/generated/` first, regenerated
both). `make lint typecheck test` clean on both stacks, 75 backend tests +
2 frontend tests.

Next: Phase 2 — frontend core (canvas & CRUD). First unchecked box is "Theme
system: CSS-variable tokens, industrial default, light + dark, theme
switcher." PR #2 (Phase 1a) is still open pending gradius's review; this
session's work should go up as its own PR against `main` (or rebased onto
main once #2 merges — gradius's call on sequencing).

## 2026-07-23 — Phase 1a: settings, models, Alembic, auth, entity types

Phase 1 is too large for one session (7 checkboxes: schema, auth, entity types,
full CRUD, events/WS, OpenAPI/client gen, comprehensive authz matrix), so split it —
this session is "1a," covering the first three PLAN checkboxes on
`phase-1a-models-auth`. Before starting, gradius pushed `phase-0-scaffolding`,
opened PR #1, watched CI go green for the first time (confirmed the pnpm risk flagged
last session never materialized), and merged it — first real `main` history beyond
the initial commit. `gh` is now installed and authenticated via a fine-grained PAT
scoped to just this repo (not gradius's whole account) per their request.

**Landed:**
- `pydantic-settings` config; the full Phase 1 SQLAlchemy 2.0 domain model (users,
  sessions, api_keys, case_members, entity_types, cases, nodes, edges, groups,
  group_members, waypoints, notes, events); an Alembic baseline migration verified
  upgrade→downgrade→upgrade against real Postgres, not just autogenerated and trusted.
- Auth: argon2id passwords, DB-backed session cookies (custom-header CSRF mitigation
  per ARCHITECTURE §5, not signed cookies — sessions are revocable DB rows, matching
  the `sessions` table already being in the schema), hashed API keys with a
  `read_only` scope flag. `case_members` RBAC (owner/editor/viewer) enforced in
  `services/cases.py`, exercised by a minimal case service (create/get/list,
  add/remove member) — full node/edge/etc CRUD is 1b's job.
- Entity type registry: the 13 ARCHITECTURE §3 builtins seeded via a data-only
  migration; full CRUD for custom types with real JSON Schema validation
  (`jsonschema`, 422 on a malformed schema); builtins immutable via the API.
- Real-Postgres integration test infra: a disposable `<db>_test` sibling database,
  per-test transaction rollback via savepoints, `httpx.AsyncClient` + dependency
  override wired to the same transaction (multiple client instances = multiple
  "logged in browsers" sharing one test's DB state). CI now runs a `postgres`
  service container. 35 backend tests, all real Postgres, no mocks.

**Surprises / notes for next session:**
- **Alembic autogenerate gotcha, confirmed for real, not just in theory**: a shared
  Postgres ENUM type (`created_via`, used by both `nodes` and `edges` via
  `ProvenanceMixin`) creates fine on `upgrade` (SQLAlchemy's checkfirst logic
  dedupes), but the autogenerated `downgrade()` drops tables and never drops the
  ENUM types — a downgrade-then-upgrade cycle fails with "type already exists."
  Fixed by hand-adding explicit `sa.Enum(name=...).drop(checkfirst=True)` calls to
  the baseline migration's downgrade. Worth checking every future migration that
  touches an enum-typed column.
- `env.py` originally always overwrote `sqlalchemy.url` from `Settings()`,
  silently ignoring any URL a caller set on the `Config` object first — only found
  this writing the migration-seed test (which drives Alembic against a disposable
  database, not the dev DB). Fixed to only fill in the default when unset.
- **API key "scope" is underspecified** in ADR-009/ARCHITECTURE — implemented as a
  single `read_only: bool` rather than inventing a fuller permission taxonomy.
  Flagging for the architect: is per-case key scoping (vs. inheriting the user's
  case roles) wanted before this ships?
- `make test` for the backend now needs a reachable Postgres (integration tests, no
  mocks, per ARCHITECTURE §9) — updated CLAUDE.md's Commands section, which
  previously (accurately, for Phase 0) claimed no Docker was ever needed for `test`.
- No admin/superuser concept exists in the data model yet, so entity-type management
  (`POST/PATCH/DELETE /entity-types`) is open to any authenticated write-capable
  user, not gated to some notion of admin. Flagging in case that's wrong for a
  multi-user single-tenant deployment — nothing in PLAN/ARCHITECTURE specifies it
  either way.

**Exit criteria demonstrated** (curl walkthroughs pasted in-session, not just
asserted): register → cookie session → create case → invite a second user as
viewer → viewer blocked from a write action (403) → mint an API key → Bearer auth
works with zero cookies; entity-type list shows all 13 builtins, custom type
creation validates its JSON Schema (422 on garbage). `make lint typecheck test`
clean on both stacks.

Next: Phase 1b — full REST CRUD for nodes/edges/notes/waypoints/groups (provenance
mandatory throughout, dedup on canonical_value), the event log +
`/ws/cases/{id}` broadcast via pg LISTEN/NOTIFY with replay-from-seq, OpenAPI
polish + `make api-client`, and the comprehensive role×action authz matrix test
(now possible once all the actions it needs to matrix against actually exist).

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

**Post-review follow-up (same day):** gradius asked for a self-review; it surfaced two
process violations (no scope statement before coding, commits/ticks batched at the
end) and several loose ends. Addressed in follow-up commits: Biome upgraded to 2.5.5
(public/ excluded from checks — Biome 2 lints standalone SVGs), `.env.example` added
(plus `--project-directory .` on compose so a root `.env` is actually read — compose's
default project dir is deploy/, and this compose version resolves the file's relative
paths against the project dir, so compose paths became root-relative), the founding
product brief moved from README.md to `docs/notes/2026-07-23-original-product-brief.md`
with a real README in its place, a note filed on Temporal sharing the app Postgres
superuser (`docs/notes/2026-07-23-temporal-postgres-credentials.md`, feeds Phase 6),
and CLAUDE.md's session-lifecycle rules hardened from advisory to structural (scope
statement is a required visible deliverable; checkpoint rule for per-checkbox
commits). Still open from the review: CI has never actually run (branch not pushed) —
verify it goes green on first push, and watch for a pnpm/action-setup "multiple
versions" conflict between its `version` input and package.json's `packageManager`
field; if it errors, drop the `version:` input from ci.yml.

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
