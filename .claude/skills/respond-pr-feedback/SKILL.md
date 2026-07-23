---
name: respond-pr-feedback
description: Address review feedback on a PR — triage each finding, fix it (or record why not), commit locally. Never pushes or posts to GitHub on its own, since the branch is often handed off to another agent/session. Use when the user says "respond to that feedback", "/respond-pr-feedback", or asks you to act on a review that was just run or posted to a PR.
---

# respond-pr-feedback

Turn review findings into committed fixes, without assuming you own the next step
(push, reply, re-request review) — that's frequently someone else's call, especially
when the branch is being handed to another agent.

## Gather the feedback

If a review just ran in this conversation (e.g. via `/review-pr` or `/review-security`),
use those findings directly — don't re-fetch or re-derive them. Otherwise, get the
feedback from its source:

```
gh pr view <n> --json reviews,comments
gh api repos/{owner}/{repo}/pulls/<n>/comments   # inline/file-anchored comments
```

If neither applies (no PR, no prior review in-session), ask the user where the
feedback lives rather than guessing.

## Triage each finding

Before touching code, state a triage decision for every finding — this is a visible
checkpoint, same spirit as the scope statement in CLAUDE.md's session lifecycle:

- **Fix** — a code/doc change addresses it directly.
- **Push back** — the finding is wrong, out of scope, or based on a misreading; write
  the reasoning down (don't silently ignore it).
- **Defer** — valid, but out of scope for this session; record it as a known gap with
  an owner, not a silent drop.

For anything that lands in CLAUDE.md's "When to stop and ask" categories (security-
sensitive work, schema changes, new dependencies, deviating from PLAN/DECISIONS, real
ambiguity) — don't resolve it by fixing code. Surface it to the user with options and
a recommendation, same as any other session work.

## Apply fixes

Hold fixes to the same rubric the review used: CLAUDE.md non-negotiables (service-layer
rule, provenance, typed everything, additive migrations), tests shipped in the same
commit as the fix, no scope creep beyond what the finding actually asks for.

Commit per finding or logical unit, not one giant commit — CLAUDE.md's checkpoint rule
applies here same as any other session work: before starting the next finding, the
current one should be committed.

## Record

- `docs/JOURNAL.md` — note that a review surfaced X and what was done about it. Future
  sessions need the trail ("review found missing Y, added it"), not just a fix with no
  context.
- `docs/PLAN.md` — tick or un-tick checkboxes if the fix changes their status.
- `docs/DECISIONS.md` — append an ADR if resolving a finding forced a decision of
  consequence.
- `docs/IDEAS.md` — if a finding was deferred and worth tracking, log it there rather
  than letting it evaporate.

## Handoff

Do not push, edit the PR description, reply to review comments, or re-request review
unless the user explicitly asks — the branch may be headed to another agent or
session, and pushing on their behalf risks colliding with work you can't see. End with
a summary of what changed, what was pushed back on (and why), and what's still open.

If the user does want it published, confirm which action they mean — `git push`,
`gh pr comment` / replying to specific review threads, or re-requesting review — each
is a distinct, visible action and shouldn't be bundled into one blanket "yes."
