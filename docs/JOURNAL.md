# Development Journal

Append-only, newest entry at the top. Every working session gets an entry: what
happened, what surprised you, what's next. Write for the teammate who wasn't there.

---

## 2026-07-23 — `/review-changes` pass on `phase-2a-shell-auth`

Ran `/review-changes` against `main` on the Phase 2a branch (no PR yet). Verdict was
approve-with-nits: `make lint typecheck test` clean (15 Vitest tests, matching the
actual count — see below), conventions held, no new backend security surface (the
frontend just calls the already-reviewed Phase 1 auth endpoints; confirmed no
token/session data touches `localStorage`, only the theme preference does). Four nits,
all fixed:

- JOURNAL's previous entry claimed 19 Vitest tests; the real count is 15. Corrected.
- Theme flash-prevention logic is necessarily duplicated between `index.html`'s inline
  pre-hydration script and `state/themeStore.ts` (the inline script can't import a
  module — it has to run before any JS loads). Added comments in both files
  cross-referencing the other, so a future change to the storage key or fallback rule
  doesn't silently update only one side.
- `authedLayoutRoute` and `caseDetailRoute` had no `errorComponent`, so a loader/guard
  failure (dead case ID, `/auth/me` network error) fell through to TanStack Router's
  unthemed default error UI. Added `components/RouteError.tsx` (themed panel, reuses
  `apiErrorMessage`, `reset()` wired to a Retry button) and wired it into both routes.
- Focus-outline width was hardcoded `2px` in two stylesheets while every other
  border-ish value went through a token. Added `--focus-width` to `theme/tokens.css`
  and switched both call sites to it.

No pushback, no deferrals — all four were small and in-scope. Not pushing or
re-requesting review; that's gradius's call.

## 2026-07-23 — Phase 2a: theme system, Berkeley Mono, auth + case-list app shell

Phase 1 was fully merged to `main`, so this session opened Phase 2 (frontend core).
Split it into 2a/2b up front (confirmed with gradius) since the full checklist —
theme, fonts, auth, canvas, inspector, WS sync, command palette, both test layers —
was too much for one sitting, mirroring how Phase 1 became 1a/1b. This session
(`phase-2a-shell-auth`) covered the app shell: theme system, Berkeley Mono, and
auth/case-list wired to the real API through TanStack Router + Query. Canvas,
inspector, WS live-sync, command palette, and Playwright e2e are 2b.

Built: CSS-variable theme tokens (industrial look, sharp corners, light/dark via
`[data-theme]`), a Zustand store for the toggle persisted to `localStorage` with a
blocking inline `<head>` script so there's no flash of the wrong theme on load;
Berkeley Mono wired via `@font-face` from `frontend/public/fonts/`, verified to
degrade cleanly to the fallback stack when the (gitignored) files are absent — a
404 on a `@font-face` src just skips that font in the stack, no JS needed; a
code-based TanStack Router route tree (no plugin — small enough that manual
`addChildren` composition beat the codegen complexity) with a pathless authed
layout route gating `/` (case list + create) and `/cases/$caseId` (name/description
only — canvas placeholder text points at 2b) behind `/login` and `/register`; Button/
TextField/Panel primitives; an API-layer wrapper (`api/auth.ts`, `api/cases.ts`,
`api/errors.ts`) that turns the generated SDK's `{data,error}` union into
throw-on-error functions plus a FastAPI-detail-to-string formatter for both plain
strings and pydantic validation-error arrays.

**Real bug caught by actually running it, not just the test suite:** every
authenticated request 401'd with "missing client header" once wired against the
live API. `deps.py`'s CSRF mitigation (ARCHITECTURE §5: session-cookie auth requires
a custom header, since a bare cross-site fetch can't attach one without CORS
pre-approval) was never something the OpenAPI schema could describe, so
`@hey-api/openapi-ts` had no way to generate for it. Fixed with one line —
`client.setConfig({ headers: { 'X-Grid-Client': 'web' } })` in `api/client.ts` — but
it would have shipped invisibly broken if this session had stopped at `make lint
typecheck test` green without a real browser pass. Reinforces the CLAUDE.md rule
about not claiming a UI change works without driving it.

**Verification:** `make lint typecheck test` clean for both stacks. Drove the actual
app against the live compose stack (`make dev`) with a scripted headless-Chromium
pass (playwright installed ad hoc into the scratchpad — not a project dependency,
just this session's driver) through register → theme toggle → create case → case
detail → theme toggle → logout, in both themes, screenshots captured at each step,
console checked clean of unexpected errors (only the expected 401 from the
post-logout `/auth/me` probe). 15 Vitest tests: theme store (system-preference
fallback, persistence, toggle), the FastAPI-error-to-string helper, and two
router-integration suites (auth guard redirects, login/logout flow, create-case
form) that render the real route tree with the API layer mocked.

Surprises: the frontend Docker image's named `node_modules` volume doesn't pick up
new dependencies from a host-side `pnpm add` — had to `docker compose exec -e CI=true
frontend pnpm install`, which went sideways (left a stray root-owned `.pnpm-store/`
inside the bind-mounted `frontend/` — removed with `sudo rm -rf`), so ended up doing
a clean `down` + volume removal + `up --build` instead. If this recurs, that's the
faster path from the start. Also needed `sudo npx playwright install-deps chromium`
to get headless Chromium's shared libs (`libnspr4` etc.) — one-time host setup, not
a repo concern.

Left running: `make dev` is still up (db/api/frontend) for gradius to poke at
directly; `make down` to stop it.

Next: Phase 2b — canvas (React Flow wrapper + custom node components per entity
type), inspector panel, WS subscription patching the Query cache, command palette,
and the Vitest + Playwright e2e coverage for all of Phase 2 (the meaningful e2e path
— login → create case → build a graph → reload → intact — needs the canvas to exist
first).

## 2026-07-23 — PR review pass: merge #2 and #3, Phase 1 fully in `main`

Worked the review→fix→merge loop on both open Phase 1 PRs (Opus for review, Sonnet
for fixes, per gradius's process). Both are now merged into `main`; Phase 1 is
complete on `main`, not just on phase branches.

**PR #2 (Phase 1a):** approve-with-nits from review. Fixed before merge: `add_member`
could let the sole owner demote themselves (only `remove_member` had a last-owner
guard — now both share `_count_owners`); FK/unique-constraint violations
(`add_member` with an unknown user, concurrent duplicate register/entity-type create)
surfaced as raw 500s instead of clean 404/409 — now caught and translated;
`key_prefix` now derives from the full `grid_<token>` string so it matches what the
user sees; session auth now rejects deactivated users like the API-key path already
did. Merging also picked up `main`'s `chore/pr-review-skills` PR (landed while 1a was
in flight) — resolved the `docs/JOURNAL.md` conflict by keeping both sessions'
entries, newest first.

**PR #3 (Phase 1b):** was stacked on `phase-1a-models-auth`; retargeted its base to
`main` after #2 merged and merged `main` into the branch — conflicts were mechanical
(cases.py/test_cases.py: both branches touched `add_member`/tests independently,
resolved by keeping both features) except one real bug the merge surfaced:
`record_event`'s eager `db.flush()` raised the FK `IntegrityError` *before* reaching
the `try/except` added around `add_member`'s `commit()`, so the guard never fired —
fixed by wrapping `record_event` + `commit` together, not just `commit`.

Review of #3 (approve-with-nits) found a real correctness gap: `_replay` read the
backlog, *then* `websocket.accept()` + `connection_manager.subscribe()` — any event
committed in that window was neither in the backlog nor delivered live, silently
dropped for the connection's lifetime. Fixed by subscribing right after `accept()`,
before the backlog read, so the only failure mode left is a same-event double
delivery (backlog + live) in that window, which callers already need to tolerate via
seq-based dedup for reconnects. Added ADR-011 for the WS ticket auth mechanism
(should have shipped with #3 — it's a new trust boundary and CLAUDE.md wants ADRs for
those). Declined one review suggestion: shortening the WS connection's DB-session
lifetime by bypassing the `Depends(get_session)` dependency — tests override that
exact dependency for the disposable `_test` database (`tests/conftest.py`), and
calling the session-maker directly instead would've silently pointed WS DB access at
the real dev database the moment anyone wrote a WS test. Left it as a documented
known limitation instead of risking that. Also declined adding new WS
replay/authz tests this session — Starlette's sync `TestClient.websocket_connect`
would run the app in a different thread's event loop than the async `db_session`
fixture, which is exactly the event-loop-binding risk 1b's session flagged for live
broadcast; doing this safely likely wants `httpx-ws` or similar, which is a new
dependency (CLAUDE.md: stop-and-ask), not a same-session call.

**Surprises:** the record_event/IntegrityError interaction above — "wrap the commit"
isn't enough once a helper does its own flush; the whole write path needs the guard.

Next: Phase 2 — frontend core (canvas & CRUD), starting with the theme system
(CSS-variable tokens, industrial default, light + dark, switcher) per PLAN.md.

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

## 2026-07-23 — Tooling: PR review/draft skills, self-review follow-up

Added three repo-scoped Claude Code skills (`.claude/skills/`): `draft-pr` (builds a
PR body from the branch diff, mapped to PLAN checkboxes), `review-pr` (reviews an open
PR against the CLAUDE.md non-negotiables, runs `make lint typecheck test`, defers to
`review-security` for new security surfaces), and `review-security` (whole-codebase
posture review grounded in the ARCHITECTURE trust model). Docs-only, no app code
touched — none of the service-layer/provenance/typed-everything rubric applies.

Opened PR #4, then ran `/review-pr` on it as a self-review. One real finding: this
JOURNAL had no entry for the session, which CLAUDE.md requires unconditionally
("a dated entry every working session") — fixed by adding this entry. Everything else
checked out clean: `make lint typecheck test` green (a stray untracked
`frontend/openapi.json` in the working tree caused one unrelated lint failure — not
part of the diff, deleted before the real lint run), and the skills' architecture
references (ADR-007/009, ARCHITECTURE §3–§6/§10, `case_members`, argon2id, Fernet)
were cross-checked against the actual docs and are accurate.

Next: address this feedback pattern generally — built `/respond-pr-feedback` to turn
"review found X, go fix X and record it" into a repeatable skill. Then back to
Phase 1 — backend core (data model, auth, CRUD, events); first unchecked box is
"Settings via pydantic-settings; SQLAlchemy 2.0 typed models; Alembic baseline."

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
