# Grid — Architecture

> Working title "Grid"; product name undecided. Keep the Python package and npm scope
> named `grid` until a name is chosen — renaming is a mechanical find/replace we accept.

Grid is a self-hosted, single-tenant, collaborative investigation platform: an
infinitely expandable graph canvas of typed entities (domains, IPs, emails, notes, …)
connected by typed relationships, expanded by transforms, with LLMs as first-class
collaborators. Think "modern Maltego" with real multiplayer and an agent-native API.

## 1. Deployment shape

One stack per tenant. A stack is a docker-compose deployment (dev and small prod) with
a path to managed containers (GCP Cloud Run / GKE) later:

| Service    | Image / tech                          | Notes                                        |
|------------|---------------------------------------|----------------------------------------------|
| `db`       | `postgres:17` + `pgvector`            | Single source of truth. Also the audit log.  |
| `api`      | FastAPI + uvicorn (Python 3.13, uv)   | REST + WebSocket + SSE + MCP server.         |
| `worker`   | Temporal worker (same codebase)       | Runs transform + LLM workflows/activities.   |
| `temporal` | `temporalio/auto-setup`               | Dev/small-prod all-in-one; UI container too. |
| `frontend` | Vite dev server (dev) / static+Caddy (prod) | Caddy also terminates TLS in prod.     |

Why Postgres (not DuckDB): we need concurrent multi-user OLTP writes, LISTEN/NOTIFY
for event fan-out, and pgvector for LLM embeddings. DuckDB is a single-writer
analytical engine — wrong tool for the primary store, possibly useful later as an
analytics sidecar for codex-wide queries.

Prod path, in order: (1) docker-compose on a single VM (Hetzner/DO) with Caddy + pg_dump
backups → (2) GCP: Cloud SQL + Cloud Run/GKE + Temporal Cloud or self-hosted Temporal.
Nothing in the design may assume co-location beyond "services can reach Postgres and
Temporal over the network."

## 2. Backend layout

```
backend/
  pyproject.toml            # uv-managed; ruff + ty configured here
  src/grid/
    core/                   # settings (pydantic-settings), security, shared deps
    db/                     # engine, session, SQLAlchemy models, alembic/
    api/                    # FastAPI routers only — no business logic
    services/               # ALL business logic; the only writers to the DB
    events/                 # event types, emission, WS connection manager, pg LISTEN/NOTIFY bridge
    transforms/             # transform spec, registry, first-party transforms
    workflows/              # Temporal workflows + activities, worker entrypoint
    llm/                    # provider adapter, model slots, graph tools, chat
    mcp/                    # MCP server exposing graph tools to external agents
  tests/                    # pytest; integration tests hit real Postgres via compose
```

**The service-layer rule (load-bearing):** every graph mutation goes through
`services/`, which validates, writes, and emits an event. Routers, workflows, MCP
tools, and LLM tools all call services — nothing else touches the tables. This is what
makes "API is a first-class citizen" true: humans, automation, transforms, and LLMs
share one code path, one authz check, one audit trail.

## 3. Data model (core tables)

- `users`, `sessions`, `api_keys` — argon2id password hashes; API keys stored hashed,
  scoped. `case_members(case_id, user_id, role)` with roles owner/editor/viewer.
- `entity_types` — registry of node types. Builtins seeded (domain, hostname, ipv4,
  ipv6, cidr, asn, url, email, username, person, organization, hash, note); custom
  types definable with a JSON Schema for properties + display config (icon, color).
- `cases` — a case is a graph workspace.
- `nodes` — `case_id`, `entity_type`, `value`, `canonical_value` (normalized: lowercased
  domain, packed IP, …), `properties` JSONB, `position` (x, y), provenance (see below),
  `confidence`. Unique on `(case_id, entity_type, canonical_value)` — dedup is
  structural, not best-effort.
- `edges` — `case_id`, `src`, `dst`, `relationship` (typed), `label`, `properties`
  JSONB, provenance. Unique on `(case_id, src, dst, relationship)`.
- `groups` — named regions with context text; `group_members(group_id, node_id)`.
- `waypoints` — saved viewports per case (name, position, zoom) for navigation/sharing.
- `notes` — attached to node, edge, group, or case; markdown body.
- `transforms` — registry: kind (`builtin` | `remote`), manifest, config; `credentials`
  encrypted at rest (Fernet with a deployment key from env; KMS later).
- `transform_runs` — status, input node ids, params, resulting node/edge ids, logs.
- `llm_providers`, `model_slots`, `conversations`, `messages`.
- `events` — append-only log of every mutation (see §4).

**Provenance is mandatory** on nodes and edges: `created_via` (`user` | `transform` |
`llm` | `api`), plus the responsible user id, transform_run id, or conversation id.
This is a security product — every fact on the graph must answer "who says so, and
how?" It also gives us LLM-created-content flagging and the investigation timeline
for free.

## 4. Event log & realtime (server-authoritative)

Postgres is the single source of truth. Every service-layer mutation appends a typed
event row (`case_id`, `seq`, `actor`, `type`, `payload`) in the same transaction as the
write. The API broadcasts events to WebSocket subscribers of that case (pg
LISTEN/NOTIFY bridges across processes; interface kept thin in `events/` so Redis
pub/sub can replace it if ever needed).

- Clients: TanStack Query caches + a WS subscription per open case; events patch the
  cache. Reconnect replays from last seen `seq`.
- Conflicts: last-write-wins per field. Node dragging sends debounced position updates.
- Presence (cursors, selections, viewports) is ephemeral WS traffic — not persisted.
- The event log doubles as the audit trail and the "investigation timeline" replay.
- No CRDTs in MVP. If collaborative rich-text note editing is wanted later, Yjs gets
  adopted for note bodies only — never for graph structure.

## 5. API surface

- **REST** `/api/v1/…` — full CRUD on everything above. FastAPI OpenAPI schema is a
  deliverable, not a byproduct: the typed TS client is generated from it
  (`@hey-api/openapi-ts`, `make api-client`), and it's what external automation reads.
- **WS** `/ws/cases/{id}` — event stream + presence.
- **SSE** — LLM chat token streaming.
- **MCP** — the same graph tools exposed to LLMs internally are exposed as an MCP
  server (API-key auth), so Claude Code or any MCP client can operate on a case as a
  coworker with zero custom integration.

Auth: session cookie (httponly, SameSite=Lax + custom header requirement) for the app;
`Authorization: Bearer <api-key>` for automation/MCP. Authz enforced in the service
layer against case roles. Designed so OIDC/SSO/SCIM slot in later as alternative
authenticators producing the same session — do not scatter auth checks.

## 6. Transforms

A transform maps input entities → new nodes/edges. Two kinds, one spec:

**The spec (stateless HTTP, serverless-shaped):**
```
GET  /.well-known/grid/transforms
  → { transforms: [{ id, name, version, description,
       input_types: [...], output_types: [...],
       params_schema: <JSON Schema>, credentials: [names],
       timeout_s, rate_limit }] }

POST /transforms/{id}/run   (Bearer auth)
  { inputs: [{type, value, properties}], params, credentials }
  → { nodes: [...], edges: [...], logs: [...] }
```

- **First-party (builtin)** transforms live in-repo under `transforms/`, are reviewed
  code, and run in the Temporal worker — but they implement the *same request/response
  shape* internally, so any builtin can be lifted out into its own container unchanged.
- **Everything else** — user plugins, LLM-authored transforms, community integrations —
  is a remote HTTP transform. Out-of-process by construction, any language.
  Registration = paste a base URL, Grid fetches the manifest and autoconfigures.
- **Trust trajectory (decided):** the HTTP boundary is the MVP isolation model, and the
  spec is deliberately the shape of a serverless function (stateless request/response,
  manifest-described). The hardening path is running remote transforms as
  container-per-transform or Cloud Run/Lambda deployments — the spec must never grow a
  feature that breaks that (no server-side sessions, no callbacks into private APIs
  beyond the documented result shape).

**Execution flow:** UI/API/LLM requests a run → `RunTransformWorkflow` (Temporal) →
activities: resolve credentials → invoke transform (in-proc or HTTP) → merge results
through the service layer (dedup by canonical value, edges to existing nodes, full
provenance) → events stream results onto every subscriber's canvas live. Retries,
timeouts, and rate limiting are Temporal policies, not hand-rolled.

MVP builtin set: DNS forward/reverse (dnspython), RDAP for domains/IPs, crt.sh
certificate-transparency subdomain discovery (free, no key — good for demos), TLS cert
fetch/parse, plus Shodan and VirusTotal as the credentialed exemplars.

## 7. LLM layer

- **Provider adapter:** pydantic-ai (typed, provider-agnostic tool calling). Anthropic
  and OpenAI native; OpenRouter, Ollama, vLLM, LM Studio via OpenAI-compatible
  endpoints. Bring-your-own-key per provider, stored encrypted like transform creds.
- **Model slots:** deployments map named slots — e.g. `reasoning`, `fast`,
  `local-private` — to provider+model. Features reference slots, never hardcoded
  models. This is how "right model for the task" and "local-only for sensitive work"
  both work without code changes.
- **Graph tools** (shared by chat, workflows, and the MCP server): search/query nodes,
  expand neighbors, read notes/groups, create nodes+edges (provenance `llm`, flagged),
  annotate, list/run transforms, summarize a region.
- **Chat:** case-scoped conversations, persisted, SSE streaming. The agent sees case
  context via tools (discoverable), not via dumping the graph into the prompt.
- Long-running agent jobs (multi-step investigations) run as Temporal workflows —
  durable, resumable, human-interruptible.

## 8. Frontend

```
frontend/
  src/
    api/        # generated client + TanStack Query hooks
    canvas/     # React Flow wrapper, custom nodes/edges, layout (elkjs)
    state/      # Zustand stores (canvas/UI state only — server state lives in Query)
    components/ # design-system primitives, themed
    routes/     # TanStack Router
    theme/      # design tokens as CSS variables
```

- **Stack:** Vite, React 19, TypeScript strict, pnpm, Biome (lint+format), TanStack
  Router + Query, Zustand, `@xyflow/react` (React Flow), cmdk command palette,
  Vitest + Testing Library, Playwright e2e.
- **Canvas:** React Flow with custom node components per entity type. Target: smooth at
  1–2k nodes (memoized nodes, viewport culling, debounced writes). The canvas is
  wrapped behind our own renderer interface so a WebGL renderer (sigma.js/Pixi) can
  replace it for 10k+ graphs post-MVP without touching app logic.
- **Theming:** every color/spacing/font flows through CSS-variable tokens. Default
  theme: industrial — sharp 1px lines, high-contrast, usgraphics.com design language.
  Default typeface: **Berkeley Mono** (woff2 set in-repo at `berkeley-mono-web/`, to be
  moved to `frontend/public/fonts/` in Phase 2), self-hosted via `@font-face` — no
  external font fetches, ever (self-hostable security product). Font family is itself
  a theme token with a fallback stack (`ui-monospace, 'JetBrains Mono', monospace`);
  other themes may bring other fonts. Licensing note: Berkeley Mono is commercially
  licensed (U.S. Graphics), not redistributable — the font files are gitignored and
  supplied locally per clone; the fallback stack keeps the app fully functional
  without them. Light + dark from day 1;
  a11y (focus rings, contrast, reduced motion) is part of the definition of done.
- **Keyboard-first:** command palette (⌘K) is the spine; every palette action gets a
  shortcut; full keyboard graph navigation (move selection along edges) is a Phase 6
  polish item with the groundwork laid earlier.

## 9. Testing strategy

- Backend: pytest + pytest-asyncio; unit tests for services, integration tests against
  real Postgres (compose); Temporal workflow tests via the SDK's test environment;
  a transform-spec conformance kit that any transform (builtin or remote) must pass.
- Frontend: Vitest for logic/components; Playwright e2e against the full compose stack
  for critical flows (auth, node CRUD, transform run, chat).
- CI: GitHub Actions running the same `make` targets developers use — no CI-only logic.

## 10. Security notes

- Secrets: env-injected; transform/LLM credentials Fernet-encrypted at rest; never in
  logs or event payloads; KMS envelope encryption when we reach GCP.
- Authz matrix (role × action) tested explicitly.
- Rate limiting on auth and transform endpoints.
- LLM-created graph content is always provenance-flagged; prompt-injection surface
  (transform results, remote content feeding an agent) treated as untrusted input —
  agents get least-privilege tools, and destructive tools require explicit user
  confirmation.
