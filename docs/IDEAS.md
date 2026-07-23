# Ideas & Inspiration

Running list. Append freely (anyone — gradius, architect, implementer agents), date it,
credit it. Nothing here is committed work; promoting an idea means discussing it and
adding it to PLAN.md's backlog or an ADR.

- **2026-07-23 (architect)** — **MCP server over the graph API.** Any MCP client
  (Claude Code, etc.) becomes a Grid coworker with zero custom integration. Promoted
  to Phase 4.
- **2026-07-23 (architect)** — **Provenance + confidence on every fact.** `created_via`
  + actor + confidence per node/edge. Consider Admiralty/NATO source-reliability
  ratings (A–F / 1–6) as an optional grading scheme for intel-mature teams. Baseline
  provenance promoted into the core schema.
- **2026-07-23 (architect)** — **Investigation timeline replay.** The event log scrubbed
  like a video: watch a case unfold, jump the graph to any point in time. Basic
  timeline is Phase 5; full time-scrubbing is post-MVP.
- **2026-07-23 (architect)** — **Guided tours.** Ordered waypoint sequences with
  narration — "here's what we found, in order" — for handoffs and remote onboarding.
- **2026-07-23 (architect)** — **LLM report generation.** Select a region or time range
  → generated intel report with citations back to node provenance.
- **2026-07-23 (architect)** — **Standing watchers.** Long-lived Temporal workflows that
  re-run transforms on a schedule and flag diffs ("this domain's resolution changed",
  "new subdomain appeared") — turns a static case into a monitored one.
- **2026-07-23 (architect)** — **DuckDB analytics sidecar.** For codex-wide/cross-case
  analytical queries post-MVP, without burdening the OLTP store.
- **2026-07-23 (architect)** — **Graph diff between waypoints/moments.** "What changed
  since Friday?" as a first-class view.
- **2026-07-23 (architect)** — **Prompt-injection-aware agent design.** Transform
  results and scraped remote content are untrusted input to LLM tools; least-privilege
  toolsets + confirmation gates on destructive actions. Partially promoted into
  ARCHITECTURE §10.
- **2026-07-23 (implementer)** — **Case membership UI is a real gap, not deferred on
  purpose.** The backend has full case-sharing (`CaseMember` roles, add/remove/list
  members, plus a new `GET /auth/lookup?email=` to find a `user_id` from an email) but
  no frontend surface at all — no invite dialog, no member list, no role editor on
  `CaseDetailPage`. Neither Phase 2 nor Phase 5 in PLAN.md actually names this. Needs
  a PLAN.md slot (Phase 2c or folded into Phase 5) before Phase 5 collaboration work
  starts, since presence/multiplayer features assume you can already get a second
  account onto a case.
