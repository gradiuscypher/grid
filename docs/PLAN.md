# Grid — MVP Implementation Plan

This is the source of truth for build order. Work phases in order; within a phase,
checkboxes are roughly ordered. Tick boxes as you complete them. Before deviating from
this plan, read CLAUDE.md ("When to stop and ask") — deviations need approval.

Every phase ends with its **exit criteria** demonstrably true, CI green, and a
`docs/JOURNAL.md` entry.

---

## Phase 0 — Scaffolding & tooling

**Goal:** `make dev` boots the whole stack; CI enforces quality on both stacks.

- [x] Repo hygiene: `.gitignore` (python, node, env files), `.editorconfig`
- [x] `backend/`: uv project (Python 3.13), ruff + ty configured strict, pytest wired,
      FastAPI app with `/api/v1/healthz`, Dockerfile
- [x] `frontend/`: Vite + React 19 + TS strict via pnpm; Biome; Vitest; placeholder
      page that calls `/api/v1/healthz` through the dev proxy; Dockerfile (dev target)
- [x] `deploy/compose.dev.yaml`: postgres:17 (+pgvector), temporal auto-setup,
      temporal-ui, api (reload), worker (placeholder entrypoint), frontend (vite)
- [x] Makefiles (root + backend + frontend): `setup`, `dev`, `test`, `lint`,
      `typecheck`, `fmt`, `migrate`, `api-client` (stub now)
- [x] GitHub Actions: lint + typecheck + test for both stacks via make targets
- [x] Update CLAUDE.md "Commands" section to match reality

**Exit criteria:** fresh clone → `make setup && make dev` → frontend page shows healthz
OK; Temporal UI reachable; `make test lint typecheck` clean; CI green.

## Phase 1 — Backend core: data model, auth, CRUD, events

**Goal:** the full graph domain exists behind a typed, tested REST API with auth and a
live event stream. (Schema details: ARCHITECTURE §3–§5.)

- [x] Settings via pydantic-settings; SQLAlchemy 2.0 typed models; Alembic baseline
- [x] Auth: users, argon2id, session cookies, hashed+scoped API keys; auth deps;
      case_members RBAC (owner/editor/viewer) enforced in services
- [x] Entity type registry: seed builtins (domain, hostname, ipv4, ipv6, cidr, asn,
      url, email, username, person, organization, hash, note); CRUD for custom types
      with JSON Schema property validation
- [x] Service layer + REST CRUD: cases, nodes (canonicalization + dedup on
      canonical_value), edges, notes, waypoints, groups — provenance mandatory
- [x] Event log: typed events appended in-transaction by services; `/ws/cases/{id}`
      broadcasting via pg LISTEN/NOTIFY; replay-from-seq on reconnect
- [x] OpenAPI polish (operation ids, tags) + `make api-client` generating the TS client
- [x] Tests: service unit tests; API integration tests against real Postgres; authz
      matrix test (role × action)

**Exit criteria:** curl-only demo works: register → create case → add nodes/edges →
second WS client sees events live. Authz matrix test passes. Generated TS client
compiles.

## Phase 2 — Frontend core: canvas & CRUD

**Goal:** a themed, usable single-player graph UI on the real API.

- [ ] Theme system: CSS-variable tokens, industrial default (sharp lines), light +
      dark, theme switcher; font-family as a token
- [ ] Berkeley Mono: copy `berkeley-mono-web/` → `frontend/public/fonts/` (both paths
      gitignored — licensed font, supplied locally), wire `@font-face`
      (Regular/Bold/Oblique/Bold-Oblique, `font-display: swap`), fallback stack
      `ui-monospace, 'JetBrains Mono', monospace`; app must render fine when the
      files are absent; no external font fetches anywhere
- [ ] Auth screens; case list/create; TanStack Router + Query wired to generated client
- [ ] Canvas (our renderer interface wrapping React Flow): custom node component per
      entity type (icon, value, type badge, provenance marker), pan/zoom, multi-select,
      create node, connect edges, delete, drag with debounced position persistence
- [ ] Inspector panel: selected node/edge properties, notes, provenance
- [ ] WS subscription: remote/own events patch the Query cache; canvas updates live
- [ ] Command palette (cmdk): navigation + core actions; shortcut registry foundation
- [ ] Tests: Vitest for stores/components; Playwright e2e: login → create case → build
      a small graph → reload → intact

**Exit criteria:** two browser windows on one case see each other's edits live; e2e
suite green; both themes usable.

## Phase 3 — Transforms & Temporal

**Goal:** right-click a node, run a transform, watch results land on the canvas.

- [ ] Temporal worker wiring (real entrypoint), `RunTransformWorkflow`: resolve creds →
      invoke → merge via services (dedup, provenance, transform_run linkage) —
      retries/timeouts as Temporal policies
- [ ] Transform spec v1 (ARCHITECTURE §6): manifest + stateless run contract; internal
      Python protocol for builtins matching the same shape
- [ ] Credential vault: Fernet-encrypted at rest, deployment key from env; creds
      never logged or in events
- [ ] Builtins: DNS forward/reverse, RDAP (domain + IP), crt.sh subdomains, TLS cert
      fetch/parse, Shodan host lookup, VirusTotal (domain/IP/hash)
- [ ] Remote transforms: register by base URL → fetch manifest → autoconfigure;
      spec conformance test kit (runnable against builtin or remote)
- [ ] UI: node context menu + palette listing transforms filtered by entity type; run
      status indicator; results stream in via events; transform run history view
- [ ] Example remote transform in `examples/` (tiny FastAPI service) proving the spec

**Exit criteria:** seed a domain node → crt.sh + DNS transforms fan out a subdomain/IP
graph live; a credentialed transform (Shodan or VT) works; the example remote
transform passes the conformance kit and runs from the UI.

## Phase 4 — LLM integration

**Goal:** an LLM coworker in every case, and the graph exposed to external agents.

- [ ] Validate ADR-008 (pydantic-ai) against current release; confirm or revise
- [ ] Provider adapter + BYO keys (encrypted); model slots (`reasoning`, `fast`,
      `local-private`) config via API + settings UI
- [ ] Graph tools (shared toolset): search/query nodes, expand neighbors, read
      notes/groups, create nodes+edges (provenance `llm`), annotate, list/run
      transforms, summarize region
- [ ] Case chat: persisted conversations, SSE streaming, tool-call visibility in UI
      ("the LLM is showing its work"), destructive tools require user confirmation
- [ ] MCP server exposing the same tools (API-key auth) — verify with Claude Code
      against a live case
- [ ] Tests: adapter unit tests with fake providers; tool tests through the service
      layer; one e2e chat flow with a mocked model

**Exit criteria:** in-app chat can answer "what do we know about this domain?" via
tools and add flagged findings to the graph; Claude Code connected over MCP can do the
same from outside.

## Phase 5 — Collaboration & navigation

**Goal:** multiplayer feel and large-graph wayfinding.

- [ ] Presence over WS: cursors, selections, viewport indicators, user colors
- [ ] Groups/regions: create from selection, visual boundary, group context notes,
      group-scoped operations (run transform on all members)
- [ ] Waypoints: save/jump/share viewport locations; palette + shortcut navigation
- [ ] Investigation timeline: event log rendered as a browsable case history
- [ ] Auto-layout (elkjs) for transform fan-outs and on-demand tidy

**Exit criteria:** two users can work a case simultaneously with visible presence;
waypoint jumps and timeline browsing work on a 500+ node case.

## Phase 6 — Hardening, deploy, polish

**Goal:** shippable to a VM; keyboard-complete; documented.

- [ ] Keyboard-only pass: navigate canvas (move selection along edges), all palette
      actions bound, shortcut cheat-sheet overlay (`?`)
- [ ] A11y pass: focus management, contrast in both themes, reduced motion
- [ ] Perf pass: 1–2k node case stays smooth (memoization, viewport culling, profiling
      notes recorded in docs/)
- [ ] Security pass: rate limiting (auth, transforms), authz matrix re-audit, secrets
      audit (logs, events, error messages), dependency audit
- [ ] `deploy/compose.prod.yaml`: Caddy (TLS) + built frontend + api + worker +
      temporal + postgres; pg_dump backup cron; restore runbook
- [ ] Deploy guide: single VM (Hetzner/DO) walkthrough; GCP path notes (Cloud SQL,
      Cloud Run/GKE, Temporal options)
- [ ] User docs: getting started, writing a remote transform, connecting an LLM
      provider, MCP setup

**Exit criteria:** clean deploy on a fresh VM by following the guide; demo case
built start-to-finish without touching the mouse; backup/restore rehearsed.

---

## Post-MVP backlog (do not start without discussion)

- Codex / cross-case intel sharing and discovery (design doc first — identity and
  merge semantics are subtle)
- Report generation: LLM turns a region/timeline into a written intel report
- Guided tours: narrated waypoint sequences for onboarding teammates
- Container/serverless execution for remote transforms (ADR-007 trajectory)
- OIDC/SSO, SCIM
- WebGL renderer for 10k+ node graphs (swap behind renderer interface)
- Yjs for collaborative rich-text note bodies
- Entity merge/split tooling and cross-case dedup
- pgvector semantic search over notes/values; "similar entities" suggestions
- Transform marketplace / community registry
