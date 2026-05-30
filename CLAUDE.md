# CLAUDE.md

Hermes is Nazar's personal AI agent — reads/writes Obsidian notes, manages Notion, replies on Telegram and Slack, proposes self-improvements via GitHub PRs. Runs on Railway using the Nous Research Hermes Agent runtime.

## Rules

- **Spec-first.** Write `specs/NNN-feature-slug/spec.md` before any code. Read `docs/constitution.md` before decisions.
- **One feature, one branch, one PR.** Branch names: `NNN-short-slug`. No direct pushes to `main`.
- **Secrets never in the repo.** All tokens/keys in Railway Variables only.
- **MCP over custom code.** Use MCP servers for external integrations; Python only when no MCP exists.

## Repo structure

```
server.py                  # Hermes admin server
hermes/
  config/SOUL.md           # Agent identity (seeded to /data/.hermes/ on first boot)
  skills/                  # SKILL.md files (auto-discovered by Hermes)
infra/
  Dockerfile               # Build context: repo root
  start.sh                 # Container entrypoint
  docker-compose.yml       # Local dev
agents/
  finance/                 # @sova_finance_bot — separate Railway service
    finance_api/           # FastAPI + aiogram + APScheduler
    alembic/               # DB migrations
specs/                     # Feature specs
docs/constitution.md       # Project constitution
```

## Development

Docker-only. After editing `pyproject.toml`: `uv lock`.

```bash
docker build -t hermes-agent .
docker run --rm -it -p 8080:8080 -e PORT=8080 -e ADMIN_PASSWORD=changeme -v hermes-data:/data hermes-agent
```

## Python project boundaries

Never mix commands between projects:

| Project             | Root              | Commands                                                   |
|---------------------|-------------------|------------------------------------------------------------|
| Hermes orchestrator | repo root         | `uv run --dev ruff check .`                                |
| Finance sub-agent   | `agents/finance/` | `uv run ruff check finance_api/` · `uv run pytest tests/`  |

## Sub-agents

Each `agents/<name>/` has its own `Dockerfile`, `railway.toml`, `pyproject.toml`. Deployed as a separate Railway service (Root Directory = `agents/<name>/`). One PostgreSQL DB per agent on the shared `hermes-db` service.

```bash
# Build finance locally
docker build -f agents/finance/Dockerfile agents/finance/
```

## Skills

Skills are SKILL.md files in `hermes/skills/` — markdown only, no Python modules. Code goes in a companion script shelled out from the skill. Hermes auto-discovers them; no registration needed.

## Environment variables

- `PORT` · `ADMIN_USERNAME` / `ADMIN_PASSWORD` — web server
- `OPENROUTER_API_KEY` · `LLM_MODEL` — LLM provider
- `TELEGRAM_BOT_TOKEN` · `TELEGRAM_ALLOWED_USER_IDS`
- `SLACK_BOT_TOKEN` · `SLACK_APP_TOKEN`
- `HERMES_VAULT_GIT_TOKEN` — GitHub PAT for `sova-claw/hermes-vault`
- `HERMES_GITHUB_PAT` — GitHub PAT for self-update PRs

Volume `/data` — state lives at `/data/.hermes`.

## Critical gotchas

- **Volume path**: `/data/.hermes` (not `/root/.hermes`)
- **Zombie reaping**: `tini` is PID 1 — do not remove
- **Cookie auth**: HMAC secret regenerates on restart → redeploy invalidates sessions
- **PID file**: `start.sh` removes `gateway.pid` on boot; leftover file prevents Hermes from starting
- **Config merge**: `server.py` deep-merges into `config.yaml` / `.env` — never replace wholesale
- **Upgrading Hermes**: bump `HERMES_REF` in `infra/Dockerfile`, then rebuild (`/upgrade-hermes`)
