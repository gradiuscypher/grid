# Decision Log

ADR-lite. Append-only; newest at the bottom. When a decision of consequence is made
(by gradius, the architect model, or an implementer agent with approval), record it
here: context, decision, consequences. Supersede — don't edit — old entries.

---

## ADR-001: Monorepo with Make-driven tooling — 2026-07-23 — Accepted

**Context:** Single product, two stacks, agent-implemented. Agents need one obvious way
to run anything.
**Decision:** One repo: `backend/` (uv, ruff, ty, pytest), `frontend/` (pnpm, Biome,
Vite, Vitest, Playwright), `docs/`, `deploy/`. All routine operations behind `make`
targets at root and per-stack. Docker compose for the dev stack. GitHub Actions CI runs
the same make targets.
**Consequences:** CLAUDE.md's command list stays authoritative; no CI-only scripts.

## ADR-002: PostgreSQL (+pgvector) as the only datastore — 2026-07-23 — Accepted

**Context:** Considered DuckDB, Postgres, graph DBs. Needs: concurrent multi-user
writes, pub/sub fan-out, embeddings, trivial deploy anywhere.
**Decision:** Postgres 17 with pgvector. Graph stored relationally (nodes/edges tables,
JSONB properties). No dedicated graph DB — traversals at 1–2k nodes/case are trivial
with recursive CTEs.
**Consequences:** One stateful service per stack (plus Temporal's, which also runs on
Postgres). DuckDB may reappear post-MVP as an analytics sidecar for codex-wide queries.

## ADR-003: SQLAlchemy 2.0 (typed) + Alembic — 2026-07-23 — Accepted

**Context:** ORM vs raw SQL.
**Decision:** SQLAlchemy 2.0 typed declarative models + Alembic migrations. Queries
live in the service layer, so dropping to textual SQL for hot paths remains a local
decision, not an architecture change.
**Consequences:** Migrations are additive revisions, never edited after merge.

## ADR-004: Temporal from day 1 — 2026-07-23 — Accepted (gradius)

**Context:** Transform chains, LLM agent jobs, and future automation want durable,
retryable, long-running execution. Alternative was a Postgres-backed queue behind an
interface, migrating later.
**Decision:** Temporal (temporalio Python SDK; `temporalio/auto-setup` in compose) is
the execution engine for all background work from the start. No second queue system.
**Consequences:** Every tenant stack carries Temporal; implementer agents must learn
workflow/activity discipline (determinism in workflows, side effects in activities).
In exchange: retries, timeouts, rate limits, and human-in-the-loop signals are
configuration, not code.

## ADR-005: React Flow canvas behind a renderer abstraction — 2026-07-23 — Accepted (gradius)

**Context:** Canvas tech is the highest-risk frontend choice. MVP target is 1–2k nodes.
**Decision:** `@xyflow/react` with custom DOM node components; our own thin renderer
interface wraps it. WebGL (sigma.js/Pixi) is the post-MVP path for 10k+ graphs.
**Consequences:** Richest node UI and best-documented path now; a perf ceiling we've
consciously accepted and isolated.

## ADR-006: Server-authoritative sync over an append-only event log — 2026-07-23 — Accepted (gradius)

**Context:** Multiplayer graph editing: CRDT (Yjs) vs server-authoritative.
**Decision:** All mutations go through the service layer, append a typed event (same
transaction), and broadcast over WebSocket. Last-write-wins per field. Presence is
ephemeral WS traffic. No CRDTs for graph structure, ever; Yjs may later serve
collaborative rich-text note bodies only.
**Consequences:** One source of truth; API-first holds; event log doubles as audit
trail and investigation timeline. Offline editing is out of scope.

## ADR-007: Transform trust boundary is HTTP; spec shaped for serverless — 2026-07-23 — Accepted (gradius)

**Context:** Users and LLMs will author transforms; unreviewed code must not run inside
the worker of a security product.
**Decision:** Only first-party, in-repo transforms execute in-process. All third-party
and LLM-authored transforms are remote HTTP transforms conforming to the manifest +
stateless run spec (see ARCHITECTURE §6). The spec is deliberately the shape of a
serverless function; the hardening path is container-per-transform / Cloud Run
execution, and no spec feature may break statelessness.
**Consequences:** One plugin API, any language, autoconfigurable via discovery
endpoint. Builtins implement the same shape internally so they can be lifted out.

## ADR-008: pydantic-ai + model slots for the LLM layer — 2026-07-23 — Provisional

**Context:** Need typed, provider-agnostic tool calling across Anthropic, OpenAI,
OpenRouter, and local OpenAI-compatible servers, with per-task model routing and BYO
keys.
**Decision:** pydantic-ai as the agent/tool framework; named model slots (`reasoning`,
`fast`, `local-private`, …) mapped to provider+model per deployment; features reference
slots only.
**Consequences:** Revisit at Phase 4 start — validate streaming, tool-call ergonomics,
and local-model support against the then-current release before committing. Slots are
the durable part of this decision; the framework is swappable.

## ADR-009: Auth — sessions + API keys now, OIDC-shaped for later — 2026-07-23 — Accepted

**Context:** Multi-user single-tenant; simple now, SSO/SCIM later; strong authz from
day 1.
**Decision:** argon2id passwords, httponly session cookies for the app, hashed scoped
API keys for automation/MCP. Case-level RBAC (owner/editor/viewer) enforced in the
service layer only — one enforcement point. Authenticators are pluggable so OIDC later
produces the same session object.
**Consequences:** No auth logic in routers or frontend beyond redirect; authz matrix is
an explicit test artifact.

## ADR-010: Single-tenant stacks (from product brief) — 2026-07-23 — Accepted (gradius)

**Decision:** One full stack per tenant; no multi-tenant data model. Isolation is
deployment-level — the right posture for a security product and radically simpler
code.
**Consequences:** No `tenant_id` anywhere. Cross-graph sharing ("codex") is a
deliberate, explicit federation feature between cases within a stack (and later
between stacks), never an accident of shared tables.

## ADR-011: WebSocket auth via short-lived REST-minted tickets — 2026-07-23 — Accepted (gradius)

**Context:** `/ws/cases/{id}` (Phase 1b, ARCHITECTURE §4's event broadcast) needs the
same trust level as the rest of the API, but the app's CSRF mitigation (ADR-009: a
custom header on cookie requests) can't ride along on a WebSocket handshake — browsers
don't let JS attach custom headers to it. ARCHITECTURE §5 didn't specify a WS auth
mechanism. Alternative considered: Origin-header validation on the handshake.
**Decision:** A short-lived (30s TTL), single-use, cryptographically random ticket
(`POST /api/v1/ws-tickets`, itself cookie+CSRF-header authenticated) that the client
passes as a `ticket` query param on the WS URL. `redeem_ticket` consumes it exactly
once and resolves to the minting user's id. Tickets live in an in-process dict
(`events/tickets.py`), matching the current single-API-process compose topology.
**Consequences:** WS auth reuses the existing session/CSRF trust chain instead of a
parallel Origin-allowlist mechanism. The in-memory ticket store means this breaks if
the API ever runs multiple replicas — would need to move to Postgres or Redis first.
