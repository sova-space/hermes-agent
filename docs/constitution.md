<!--
SYNC IMPACT REPORT
==================
Version change: (template) → 1.0.0
Added sections:
  - Core Principles (I–VIII)
  - Deployment & Cost Constraints
  - Development Workflow
  - Governance
Modified principles: N/A (initial ratification)
Removed sections: N/A
Templates reviewed:
  - .specify/templates/plan-template.md ✅ compatible (Constitution Check section present)
  - .specify/templates/spec-template.md ✅ compatible (no changes needed)
  - .specify/templates/tasks-template.md ✅ compatible (no changes needed)
Deferred TODOs: none
-->

# Hermes Constitution

## Core Principles

### I. Hermes Runtime — Do Not Fork

The Hermes Agent runtime from Nous Research MUST be used as-is. It MUST NOT be forked,
vendored, or patched. Configuration only. When Hermes behavior is uncertain, the system
MUST consult https://hermes-agent.nousresearch.com/docs rather than relying on prior
knowledge or assumptions.

### II. Single Repo, Scoped Token

The system uses one GitHub repository: `sova-claw/hermes-agent` — code, specs, Dockerfile, Railway config.

The agent's PAT (`HERMES_GITHUB_PAT`) MUST be scoped to `sova-claw/hermes-agent` only with
`contents:write` and `pull_requests:write`. No token stored in the repo or committed to git.

### III. Volume-Only Persistence

All persistent application state MUST live under the Railway volume mounted at
`/data/.hermes`. No application state MUST be written outside this path. This ensures
data survives container restarts without additional storage services.

### IV. No Secrets in Repository

No credential, token, API key, or secret MUST ever be committed to either repository,
including in `.env.example` files. All secrets MUST be provided via Railway environment
variables or the Hermes dashboard. Placeholder names only (e.g., `<your-token-here>`) are
permitted in documentation.

### V. MCP-First Integrations

All external integrations (GitHub, Slack, etc.) MUST be added as MCP servers configured
through the Hermes dashboard or `config.yaml`. Bespoke Python integrations are forbidden.
Exception: when no MCP server exists for a required capability, a Hermes skill MUST be
written instead.

### VI. PR-Only Changes — No Direct Pushes

All code changes MUST flow through pull requests against the `main` branch of
`sova-claw/hermes-agent`. Direct pushes to `main` are forbidden and MUST be blocked by
branch protection. When the agent proposes changes to the repository, it MUST create a
branch named `hermes-proposal/<short-slug>` and open a PR. It MUST NOT push to `main`
directly, even if the branch protection rule is temporarily disabled.

### VII. Spec-First Development

Every feature MUST have a `specs/NNN-feature-slug/spec.md` written and reviewed before any
code is written. The spec covers what it does, acceptance criteria, and open questions.
One feature per branch (`NNN-short-slug`), one PR per branch.

### VIII. Python Quality Gates

Python code MUST target Python 3.11+. All function signatures MUST have type hints. Code
MUST pass `ruff check` and `ruff format` with default rules before merge.

## Deployment & Cost Constraints

Railway's one-month trial budget is a hard constraint. Any feature that would add a second
always-on Railway service MUST be explicitly approved by the user with a documented cost
impact estimate before being specified. Default assumption: one service, one volume, no
additional paid add-ons.

## Development Workflow

- Feature branches: `NNN-short-slug`
- Agent proposal branches: `hermes-proposal/<slug>`
- Spec: `specs/NNN-feature-slug/spec.md` (one file, required before code)
- All PRs require at least one human review before merge

## Governance

This constitution supersedes all other practices. Amendments require:
1. A PR updating this file with a version bump and updated `Last Amended` date
2. A Sync Impact Report (as an HTML comment at the top of this file)
3. Review and approval before merge

**Versioning policy**:
- MAJOR: backward-incompatible removal or redefinition of a principle
- MINOR: new principle or section added
- PATCH: clarification, wording, typo fix

All PRs and reviews MUST verify compliance with the active constitution version. If a spec
or plan conflicts with this constitution, the constitution wins — update the spec, not the
constitution, unless an amendment is warranted.

**Version**: 1.0.0 | **Ratified**: 2026-05-25 | **Last Amended**: 2026-05-25
