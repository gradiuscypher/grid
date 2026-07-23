---
name: draft-pr
description: Draft a pull request for the current branch — complete coverage of every change with the technical detail a reviewer needs, but no filler. Use when the user says "draft a PR", "/draft-pr", or is ready to open a PR for the current branch's work.
---

# draft-pr

Draft a PR for the current branch against `main`. Goal: **cover every change with
enough technical detail to review it, and nothing more.** When in doubt about whether a
detail matters, include it — but never pad with restatement, marketing, or a
blow-by-blow of the diff a reviewer can read themselves.

## Gather

Run these together and read the actual changes — do not summarize from memory:

```
git fetch origin main --quiet
git log --oneline origin/main..HEAD
git diff origin/main...HEAD --stat
git diff origin/main...HEAD
```

Also read the latest `docs/JOURNAL.md` entry and the relevant `docs/PLAN.md`
checkboxes — the PR should map to the plan.

If the branch isn't pushed (`git status -sb` shows no upstream, or it's behind), push
with `git push -u origin HEAD` before creating the PR. Don't force-push without asking.

## Write the body

Keep it tight. Use only the sections that carry real information for *this* change —
drop any that would be empty. Prefer the technical fact over the sentence describing it.

```
## Summary
1–3 sentences: what this PR does and why. Reference the PLAN phase/checkbox(es) it
completes (e.g. "Completes Phase 1b: service-layer CRUD + event log").

## Changes
Grouped by area (backend / frontend / docs / infra), one bullet per logical change,
each with the technical specifics a reviewer needs — new endpoints, service functions,
tables, event types, components, config. Not a file-by-file recap.

## Schema / migrations
Alembic revision id(s) and what they add. Omit if none. Flag anything not additive.

## Tests
What's covered and how (unit vs. integration-against-real-Postgres). Name notable
cases (e.g. authz matrix, dedup on canonical_value). Note gaps you're deferring.

## Security-sensitive surfaces
Only if the PR touches authn/authz, secrets, transform execution, the trust boundary,
or LLM tool exposure. Name the surface and how the invariant is upheld. This flags the
PR for `/review-security`.

## Notes / deferred
Anything intentionally left for a later PR, known limitations, or follow-ups with an
owner. Omit if none.
```

Match the repo's conventions when judging what's "security-sensitive" — see the
non-negotiables in `CLAUDE.md` and ARCHITECTURE §10.

## Create it

Show the drafted title and body to the user first. On confirmation, create it as a
**draft PR** so review is deliberate:

```
gh pr create --draft --base main --title "<title>" --body "<body>"
```

End the PR body with:

```
🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

Report the PR URL. Do not mark it ready-for-review or merge it — that's gradius's call.
