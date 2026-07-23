---
name: review-pr
description: Review an open pull request for code quality and correctness — enforces this repo's conventions, checks tests exist and pass and still reflect the working app, triggers /review-security for new security surfaces, and verifies agent + human docs are current. Use when the user says "review PR", "/review-pr", or asks for a review of an open PR.
---

# review-pr

Review an open PR for **quality and correctness**, held to *this repo's* standards —
not generic advice. If an argument names a PR (number or URL), review that; otherwise
list open PRs (`gh pr list`) and confirm which one, defaulting to the PR for the current
branch (`gh pr view`).

## Load the change and its context

```
gh pr view <n> --json title,body,headRefName,baseRefName,files,additions,deletions
gh pr diff <n>
```

Then read, in the repo, whatever the diff touches plus:
- `CLAUDE.md` — the non-negotiable conventions (these are the review rubric).
- `docs/PLAN.md` — which checkbox(es) this claims to complete.
- `docs/ARCHITECTURE.md` / `docs/DECISIONS.md` — for anything the change interacts with.

Check out the branch locally so you can run things: `gh pr checkout <n>`.

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
   concurrency. Does it actually do what the PR says?

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

4. **Security surfaces.** If the PR adds or changes any security-sensitive surface —
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
and the test-run result. Offer to post it as a PR review (`gh pr review`) — post only on
confirmation, and never approve on the user's behalf without them saying so.
