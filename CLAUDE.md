# CLAUDE.md

This file provides guidance to Claude Code when working in this repository.

## Purpose

Hermes is Nazar's personal AI agent — a self-contained assistant that can read and write his Obsidian notes, manage Notion, reply on Telegram and Slack, and propose improvements to its own codebase via GitHub PRs.

The agent runs on Railway using the Nous Research Hermes Agent runtime. This repo adds configuration, custom skills, and deployment wiring on top of it — the runtime itself is never forked or modified.

## How we work

**Spec-first.** No code is written without a spec. Write a brief spec in `specs/NNN-feature-slug/spec.md` before implementation. Constitution is the source of truth — read `docs/constitution.md` before making decisions.

**One feature, one branch, one PR.** Branches named `NNN-short-slug`. Specs in `specs/NNN-feature-slug/`. No direct pushes to `main`.

**Secrets never in the repo.** All tokens and API keys live in Railway Variables only.

**MCP over custom code.** External integrations use MCP servers configured in the Hermes dashboard or `config.yaml`. Custom Python only when no MCP server exists for the capability.

**Simple over clever.** Python 3.11+, type hints on all signatures, ruff-clean. No over-engineering — this has one user.

## What this repo is

**Hermes** — a personal AI agent deployed on Railway. This repo (`sova-claw/hermes-agent`) contains:
- `server.py` — Python admin server that manages and reverse-proxies the upstream Hermes Agent runtime
- `skills/` — custom Hermes skills (SKILL.md format, baked into the Docker image)
- `specs/` — feature specs (spec.md, plan.md, tasks.md per feature)
- `docs/constitution.md` — project constitution

A second repo, `sova-claw/hermes-vault`, holds the private Obsidian vault. It is accessed only by the `obsidian-vault` skill using `HERMES_VAULT_GIT_TOKEN`.

## Repository structure

```
server.py                      # Admin server (single file)
start.sh                       # Container entrypoint
Dockerfile                     # Builds the image; copies skills/ into /data/.hermes/skills/
pyproject.toml / uv.lock       # Python deps (managed with uv)
.mcp.json                      # Project-level MCP servers for Claude Code
skills/
  SOUL.md                      # Agent identity — PR-only self-update rules
  obsidian-vault/
    SKILL.md                   # Skill declaration (auto-discovered by Hermes)
    vault.py                   # Git-backed vault implementation (stdlib only)
specs/
  001-railway-bootstrap/       # Existing Railway setup documentation
  002-notion-mcp/              # Notion MCP config and OAuth flow
  003-obsidian-skill/          # Obsidian vault skill spec and plan
  004-self-update-loop/        # GitHub MCP + agent self-update workflow
docs/
  constitution.md              # Project constitution (v1.0.0)
  morning-summary.md           # Post-bootstrap action list
  bootstrap-brief.md           # Original setup brief (historical)
```

## Development workflow

Development is Docker-only — no local Python virtualenv.

Dependencies are managed with `uv`. After editing `pyproject.toml`:
```
uv lock
```

**Build:**
```
docker build -t hermes-agent .
```

**Run locally:**
```
docker run --rm -it -p 8080:8080 -e PORT=8080 -e ADMIN_PASSWORD=changeme -v hermes-data:/data hermes-agent
```

## Hermes skills

Skills live in `skills/` and are copied into `/data/.hermes/skills/` at image build time (see Dockerfile). Hermes auto-discovers them — no `config.yaml` registration needed.

Skills are **SKILL.md files** (markdown with YAML frontmatter `name` and `description`). They are declarative agent instructions, not Python. If a skill needs to run code, it shells out to a companion script (e.g., `vault.py`).

## Feature workflow

No code without a spec. Create `specs/NNN-feature-slug/spec.md` covering what it does, acceptance criteria, and open questions. Then implement on branch `NNN-short-slug` and open a PR.

## Branch conventions

- Features: `NNN-short-slug`
- Agent self-proposals: `hermes-proposal/<slug>`
- No direct pushes to `main` — PRs only

## Upgrading Hermes

Bump `HERMES_REF` in `Dockerfile`, then rebuild. See `/upgrade-hermes` for the full workflow.

## Environment variables

All secrets live in Railway Variables — never committed to the repo.

- `PORT` — web server port (default 8080)
- `ADMIN_USERNAME` / `ADMIN_PASSWORD` — dashboard basic auth
- `OPENROUTER_API_KEY` — LLM provider
- `LLM_MODEL` — model identifier (e.g. `openai/gpt-4o-mini`)
- `TELEGRAM_BOT_TOKEN` — Telegram bot
- `TELEGRAM_ALLOWED_USER_IDS` — allowed Telegram user IDs
- `SLACK_BOT_TOKEN` / `SLACK_APP_TOKEN` — Slack Socket Mode
- `HERMES_VAULT_GIT_TOKEN` — GitHub PAT for vault repo (`sova-claw/hermes-vault`)
- `HERMES_GITHUB_PAT` — GitHub PAT for agent self-update PRs (`sova-claw/hermes-agent`)

Volume: `/data` — Hermes state lives at `/data/.hermes`.

## MCP servers (Claude Code)

Defined in `.mcp.json` at repo root:
- `railway` — Railway HTTP MCP (`https://mcp.railway.com`)
- `railway-cli` — Railway stdio MCP (`npx @railway/mcp-server`)

Add new MCPs to `.mcp.json`. Restart Claude Code after changes.

## Critical gotchas

**Volume path**: State lives at `/data/.hermes` (`HOME=/data`, `HERMES_HOME=/data/.hermes`). Not `/root/.hermes`.

**Zombie process reaping**: Container uses `tini` as PID 1. Do not remove — Hermes spawns subprocesses and without tini the PID table exhausts.

**Cookie-based auth**: Admin server uses HMAC-signed cookies. The signing secret regenerates on every process start, so redeploying invalidates all sessions.

**PID file race**: `start.sh` removes `/data/.hermes/gateway.pid` on boot. The volume survives restarts but Hermes doesn't clean up the PID file on SIGTERM — leaving it causes Hermes to refuse to start.

**Pre-built TUI**: React dashboard compiled at image build time. `HERMES_TUI_DIR=/opt/hermes-agent/ui-tui` tells Hermes where to find it. Do not move during builds.

**Config deep-merge**: `server.py` deep-merges into `/data/.hermes/config.yaml` and `/data/.hermes/.env` on startup without overwriting user-set keys. Do not replace these files wholesale.

**Reverse proxy headers**: Proxy preserves `Authorization` and `Cookie` intentionally — Hermes dashboard relies on them.

<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan
<!-- SPECKIT END -->
