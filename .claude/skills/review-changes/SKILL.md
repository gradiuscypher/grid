---
name: review-changes
description: Review the current branch's changes against main for code quality and correctness — enforces this repo's conventions, checks tests exist and pass and still reflect the working app, triggers /review-security for new security surfaces, and verifies agent + human docs are current. No PR required. Use when the user says "review my changes", "/review-changes", or asks for a review of the current branch's diff.
---

# review-changes

Review the current branch's changes **against `main`**, held to *this repo's* standards
— not generic advice. No PR required: this reviews whatever exists on the branch right
now, committed or not.

## Load the change and its context

```
git fetch origin main --quiet   # skip silently if there's no remote / it fails
git status -sb
git log --oneline main..HEAD
git diff main...HEAD --stat
git diff main...HEAD
```

If `git status` shows uncommitted changes, say so explicitly and default to including
them in the review (`git diff main...HEAD` plus working-tree diff) — that's usually
what "review my changes" means — but call out that you're doing so rather than silently
picking a scope.

Then read, in the repo, whatever the diff touches plus:
- `CLAUDE.md` — the non-negotiable conventions (these are the review rubric).
- `docs/PLAN.md` — which checkbox(es) this claims to complete.
- `docs/ARCHITECTURE.md` / `docs/DECISIONS.md` — for anything the change interacts with.

You're already on the branch — no checkout step needed.

## Review dimensions

Work through each; report findings with `file:line` refs and a severity
(blocker / should-fix / nit).

1. **Conventions (blocker if violated).** Hold the diff against the `CLAUDE.md`
   non-negotiables, especially:
   - **Service-layer rule** — every graph mutation goes through `services/`, which
     validates, enforces authz, writes, and emits an event *in one transaction*.
     Routers / activities / MCP / LLM tools call services; nothing else writes.
   - **Provenance mandatory** on every node/edge (creator kind + responsible actor).
   - **Typed everything** — ty and `tsc` strict; no `Any`/`any` without a constraint
     comment.
   - Migrations additive; never edit a merged one. Secrets never in code/logs/events/
     fixtures. Frontend server-state in TanStack Query, UI-state in Zustand, not both.
     Theming through CSS-variable tokens, both light and dark.

2. **Correctness.** Trace the logic, not just the shape. Edge cases, error paths,
   transaction boundaries, canonicalization/dedup, event ordering & replay-from-seq,
   concurrency. Does it actually do what it claims to?

3. **Tests ship with the feature.** Every new code surface (endpoint, service fn,
   component, event type) has tests in the same change. Integration tests hit **real
   Postgres**, not a mocked DB. Tests must assert real behavior, not tautologies.
   Then **run them and confirm green** — reality over assertion:
   ```
   make lint typecheck test        # backend test needs Postgres up:
   docker compose -f deploy/compose.dev.yaml up -d db
   ```
   Paste the actual pass/fail output into the review. If tests were changed, confirm
   they still reflect the working app rather than being loosened to pass.

4. **Security surfaces.** If the diff adds or changes any security-sensitive surface —
   authn/authz, credential/secret handling, transform execution boundary, the trust
   model, or LLM tool exposure — **invoke `/review-security`** (via the Skill tool) and
   fold its findings into this review. Don't hand-wave security inline.

5. **Documentation — agent and human.** Confirm the change kept docs honest:
   - `docs/PLAN.md` checkbox ticked when the item is actually done.
   - `docs/JOURNAL.md` entry for the session.
   - New ADR in `docs/DECISIONS.md` if a decision of consequence was made.
   - `CLAUDE.md` "Commands"/conventions updated if reality moved (new make target, etc.).
   - `docs/ARCHITECTURE.md` updated if the design diverged (should have been a
     stop-and-ask).
   - API-facing changes reflected in OpenAPI metadata / regenerated TS client; user-
     facing changes in README/frontend docs.

## Output

A structured review, findings ordered most-severe first, each with `file:line` and
severity. Lead with a one-line verdict (approve / approve-with-nits / changes-requested)
and the test-run result. There's no PR to post to — end with a plain summary the user
can act on directly. If they want the findings turned into fixes, that's
`/respond-pr-feedback` (it works from findings already in the conversation, PR or not);
don't apply fixes yourself unless asked.
