# Temporal shares the app Postgres — and its superuser (2026-07-23, Sonnet implementer)

Observation from Phase 0: `deploy/compose.dev.yaml` points `temporalio/auto-setup` at
the same Postgres instance as the app, using the same `grid` superuser credentials.
Auto-setup creates its own `temporal` and `temporal_visibility` databases with that
role.

This is fine for dev — one Postgres container, zero extra configuration. But it means:

- The Temporal server holds credentials that can read/write the entire `grid`
  application database, not just its own schemas.
- Conversely, anything that compromises the app's DB credentials also owns Temporal's
  state (workflow histories, task queues).

**Recommendation for Phase 6 (compose.prod.yaml):** create a dedicated `temporal` role
scoped to its own databases, and give the app role no access to Temporal's. Same
instance is still fine at small-prod scale; the separation is roles, not servers. On
the GCP path (Cloud SQL + Temporal Cloud or self-hosted), this separation falls out
naturally, but the compose.prod.yaml file must do it explicitly.

Filed now so the Phase 6 security pass inherits it instead of rediscovering it.
