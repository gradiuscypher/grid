---
name: review-security
description: Security review of Grid's overall posture — evaluates the whole codebase's security as a system, not just a single diff. Reads the trust model and every security-relevant surface together so findings account for the full structure. Use for "/review-security", a standalone security audit, or when /review-pr flags a new security-sensitive surface.
---

# review-security

Evaluate the **security posture of the codebase as a whole**. Even when triggered by a
specific PR, a change is only safe in context — read the full structure so a finding
reflects how the pieces actually compose, not one file in isolation. Grid is a security
product; the trust model is a feature, and this review defends it.

## Ground yourself in the intended model first

Before judging the code, read what the security model is *supposed* to be, so you
review against intent rather than inventing a rubric:
- `docs/ARCHITECTURE.md` — §3–§5 (data model, provenance, event log), §6 (transforms &
  the HTTP isolation boundary), §10 (Security notes).
- `docs/DECISIONS.md` — ADRs on the trust boundary / transform isolation (e.g. ADR-007)
  and the "trust trajectory" (HTTP boundary is the MVP isolation model).
- `CLAUDE.md` — the security non-negotiables (service-layer authz, provenance, secrets
  handling, transform spec constraints, Temporal side-effect discipline).

Note what is **out of scope by design** (deferred isolation, KMS-later, etc.) and review
against the current intended model — flag gaps against *that*, and separately flag if
the code silently undercuts a stated invariant.

## Survey the whole surface

Read the actual implementation across these areas and evaluate them together:

1. **AuthN.** Session cookies (httponly, SameSite=Lax + custom-header requirement),
   API keys (hashing at rest, scoping), password hashing (argon2id params). Session
   fixation, key leakage, timing, token entropy. One code path for all authenticators.

2. **AuthZ.** `case_members` RBAC (owner/editor/viewer) enforced **in the service
   layer** for every mutation and read path — not scattered in routers. Hunt for any
   write path that bypasses services, and any missing role check in the matrix.

3. **Secrets.** Transform/LLM credentials Fernet-encrypted at rest; deployment key from
   env; never in code, logs, event payloads, fixtures, or error messages. Grep for
   plaintext credential handling and accidental logging.

4. **Injection & input validation.** SQLAlchemy usage (no raw string SQL / f-string
   queries), JSON Schema validation on entity properties, canonicalization not
   trusting client input, WS message handling. Pydantic boundaries on all external
   input.

5. **Transform / execution boundary.** Remote transforms are stateless HTTP
   (manifest + run); confirm nothing added server-side state, callbacks, or SSRF-prone
   fetches without guardrails. Validate the isolation model matches the decided
   trajectory.

6. **LLM / prompt-injection.** Transform results and remote content feeding agents are
   untrusted input. Agents get least-privilege tools; destructive tools require explicit
   user confirmation. LLM-created graph content is provenance-flagged.

7. **Rate limiting & abuse.** On auth and transform endpoints per ARCHITECTURE §10.

8. **Provenance integrity.** Every node/edge records creator kind + responsible actor;
   no path creates anonymous facts. This is both a product and a forensic-security
   guarantee.

9. **Transport / config / deps.** Dependency risk, dangerous defaults, secrets in
   compose/env examples, CORS/CSRF posture, self-hostable "no external fetches" rule.

Use search broadly (`grep`/`Grep`) — trace each surface across `services/`, `api/`,
`core/`, `events/`, `transforms/`, `llm/`, and the DB models — rather than reading only
recently changed files.

## Report

Findings ordered by severity (critical / high / medium / low / informational), each
with `file:line`, a concrete exploit or failure scenario, and specific remediation.
Distinguish:
- **Regressions / violations** — code that breaks a stated invariant. Highest priority.
- **Gaps** — missing controls the intended model calls for.
- **Accepted risk** — deferred-by-design items; confirm they're still consistent with
  the decided trajectory, don't re-litigate them.

Do not modify code as part of the review unless the user asks. Lead with a short posture
summary (is the trust model intact?) before the itemized findings.
