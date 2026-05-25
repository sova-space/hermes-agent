# AGENTS.md

Rules for AI agents (Claude Code, Hermes, and others) working in this repository.

Human contributors should read `README.md` for orientation. This file is specifically for agents.

---

## What this project is

**Hermes** is Nazar's personal AI agent, deployed to Railway. It connects Telegram and Slack,
reads and writes his Notion workspace and Obsidian vault, and can propose changes to its own
configuration via GitHub pull requests.

The agent runtime is **Hermes Agent** from Nous Research. We do not fork or vendor it — we only configure it.

## Repository layout

```
hermes-agent/
├── AGENTS.md                        ← you are here
├── README.md                        ← for humans
├── CLAUDE.md                        ← Claude Code specific guidance
├── .mcp.json                        ← project-level MCP servers for Claude Code
├── railway.toml                     ← Railway deploy config (points to infra/Dockerfile)
├── server.py                        ← admin server (single file, manages Hermes process)
├── pyproject.toml                   ← Python deps (managed with uv)
├── hermes/                          ← Hermes runtime assets
│   ├── config/
│   │   └── SOUL.md                  ← Hermes identity; seeded to /data/.hermes/SOUL.md on first boot
│   └── skills/
│       └── obsidian-vault/
│           ├── SKILL.md             ← skill declaration (auto-discovered by Hermes)
│           ├── manifest.json        ← permissions and entrypoint declaration
│           └── vault.py             ← git-backed vault implementation
├── infra/                           ← container/CI artifacts
│   ├── Dockerfile                   ← builds image; build context is repo root
│   ├── start.sh                     ← container entrypoint
│   └── templates/
│       └── index.html               ← admin UI served by server.py
├── specs/                           ← one folder per feature (matches branch name)
│   └── NNN-feature-slug/
│       ├── spec.md
│       ├── plan.md
│       └── tasks.md
└── docs/
    ├── constitution.md              ← project constitution (source of truth)
    └── morning-summary.md           ← post-bootstrap action list
```

The Obsidian vault is in a **separate** repository (`sova-claw/hermes-vault`) and is NOT part of this repo.

---

## Hard rules — never violate

### 1. Specs before code

No file under `skills/`, no `Dockerfile` changes, no `railway.toml` changes without a
corresponding `specs/NNN-feature/` folder containing at minimum `spec.md`. The spec is the
source of truth; code is generated from it.

### 2. Branch and PR discipline

- One feature per branch. Branch names: `NNN-short-slug` (zero-padded three-digit ordinal).
- All changes go through pull requests against `main`. No direct pushes.
- Hermes self-update proposals use branch names `hermes-proposal/<slug>` and always open a PR — never push to `main`.
- Every PR must have a descriptive title and a description explaining what changed and why. Use `gh pr create --title "..." --body "..."`.
- After opening a PR, merge it yourself if the change is straightforward and doesn't need review. For complex changes, tag Nazar.

### 3. No secrets in this repo, ever

All credentials live in Railway environment variables or the Hermes dashboard. Never commit
API keys, tokens, OAuth secrets, or real values in any file. If you encounter a secret in a
file, stop and tell Nazar before doing anything else.

### 4. Token separation between repos

- `HERMES_GITHUB_PAT` — scoped to `sova-claw/hermes-agent` only. Used by GitHub MCP for self-update PRs.
- `HERMES_VAULT_GIT_TOKEN` — scoped to `sova-claw/hermes-vault` only. Used by the obsidian-vault skill.

Never propose a configuration that gives a single token access to both repositories.

### 5. MCP first, skills second

When adding a new external integration:
1. Check if an official MCP server exists. If yes, use it via Hermes config.
2. Only if no MCP exists, write a custom Hermes skill.

### 6. Cost budget is real

Railway Hobby is $5/month for one service. Any feature that would add a second always-on
Railway service requires explicit approval from Nazar with a documented cost impact in the spec.

### 7. Verify before assuming

MCP package names, Hermes config schema, and Railway behavior may shift. When in doubt:
- Hermes docs: https://hermes-agent.nousresearch.com/docs
- Railway docs: https://docs.railway.com

Docs win over this file when they conflict.

---

## Conventions

### Hermes skills

Skills live under `skills/<skill-name>/`. Each skill requires:
- `SKILL.md` — declarative agent instructions (YAML frontmatter: `name`, `description`)
- `manifest.json` — permissions and entrypoint declaration
- Companion script (e.g. `vault.py`) only if the skill needs to run code

Skills are **not** Python modules — SKILL.md files are markdown instructions for the agent.
Hermes auto-discovers them from `/data/.hermes/skills/` — no config registration needed.

### Python code (companion scripts)

- Python 3.11+, type hints on all function signatures
- `ruff check` and `ruff format` must pass before merge
- `subprocess.run` for shell operations — no heavy dependencies
- `pathlib.Path` over `os.path`
- No `print()` for diagnostics — use `logging`

### Commit messages

Conventional Commits format: `<type>(<scope>): <description>`

Types: `feat`, `fix`, `chore`, `docs`, `refactor`

Examples:
- `feat(obsidian-skill): add merge conflict handling`
- `chore(hermes): update daily note 2026-05-25`
- `docs(agents): update repository layout`

Agent-generated commits (Hermes writing to vault) use `chore(hermes):` prefix.

### Feature specs

A minimal `spec.md` covers:
- What it does (one paragraph)
- Acceptance criteria (testable, specific)
- Open questions (resolved before implementation starts)

No formal template required — clarity over ceremony.

---

## Communication style

When working in this repository, all agents should:

- Be direct. No "Great question!" or "Happy to help" preambles.
- Push back when a proposed change has a real flaw — surface it before executing.
- Match Nazar's language: Ukrainian if he writes Ukrainian, English otherwise.
- Skip disclaimers about being an AI.
- When something is unknown, say so — don't manufacture confidence.
- When a request is ambiguous, pick the reasonable option and proceed — don't ask.
- Surface tradeoffs honestly. For cost, security, or architectural decisions let Nazar decide.

## Output style

See `hermes/config/STYLE.md` for writing rules. Key points:

- No intro, filler, fluff, pleasantries.
- Short sentence fragments. Bullets for lists.
- Technical accuracy always. Code/errors/API names: never abbreviate.
- When ambiguous → pick reasonable option, proceed. Don't ask.
- PR format: `[what changed]. [why]. [how].`

Reference: https://github.com/JuliusBrussee/caveman

Nazar is a Senior SDET with strong Python. Don't over-explain basics. Solo project — PRs for traceability, not gatekeeping.

---

## Out of scope

- Multi-user deployment
- Public-facing endpoints
- Forking or modifying the Hermes runtime
- Financial transaction execution

---

## When to update this file

When hard rules, repo layout, token model, or major conventions change. Via PR, separate
from feature work. Title: `docs(agents): <what changed>`.
