# CLAUDE.md

Hermes is Nazar's personal AI agent — replies on Telegram and Slack, tracks finances, and proposes self-improvements via GitHub PRs. Runs on Railway using the Nous Research Hermes Agent runtime.

## Rules

- **Spec-first.** Write `specs/NNN-feature-slug/spec.md` before any code.
- **One feature, one branch, one PR.** Branch names: `NNN-short-slug`. No direct pushes to `main`.
- **Secrets never in the repo.** All tokens/keys in Railway Variables only.
- **MCP over custom code.** Use MCP servers for external integrations; Python only when no MCP exists.
- **Python quality.** Target Python 3.11+. All function signatures must have type hints. Pass `ruff check` + `ruff format` before merge.

## Repo structure

```
server.py                  # Hermes admin server
hermes/
  config/SOUL.md           # Agent identity (seeded to /data/.hermes/ on first boot)
  skills/finance/          # Finance skill — calls agents/finance REST API
  skills/project-context/  # Tracks active project context
infra/
  Dockerfile               # Build context: repo root
  start.sh                 # Container entrypoint
  docker-compose.yml       # Local dev
agents/
  finance/                 # @sova_finance_bot — separate Railway service
    finance_api/           # FastAPI + aiogram + APScheduler
    alembic/               # DB migrations
specs/                     # Feature specs
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

## Railway Deployment

Two separate Railway projects — both served from the same monorepo (`sova-claw/hermes-agent`):

| Component | Railway Project | Project ID |
|---|---|---|
| Hermes orchestrator | `hermes-main` | `3d73dc58-1201-4258-bc1d-1f9c24333032` |
| Finance sub-agent + DB | `finance-agent` | `186cf9f1-f88f-4b73-b286-a055e107cc9d` |

Finance project service IDs (needed for `railway link`):
- `finance-api`: `b6cb492f-9100-4330-82db-8afd95d6fe91`
- DB: `b81eaac6-f7f1-46c4-a113-b60a39e59729`
- Environment: `de3164da-54fe-4557-ae8b-bd5d1ef01a33`

```bash
# Hermes orchestrator — from repo root
railway up --detach

# Finance API — from agents/finance/
cd agents/finance
railway link --project 186cf9f1-f88f-4b73-b286-a055e107cc9d --service b6cb492f-9100-4330-82db-8afd95d6fe91
railway up --detach
```

**Railway does NOT auto-deploy on git push.** Always run `railway up --detach` after pushing.

- Do NOT deploy finance from `hermes-main` — it has no finance service
- Do NOT use `sova-claw/hermes-finance` — that repo is stale
- Do NOT create new Railway services — both already exist

## Skills

Skills are SKILL.md files in `hermes/skills/` — markdown only, no Python modules. Code goes in a companion script shelled out from the skill. Hermes auto-discovers them; no registration needed.

## Environment variables

- `PORT` · `ADMIN_USERNAME` / `ADMIN_PASSWORD` — web server
- `OPENROUTER_API_KEY` · `LLM_MODEL` — LLM provider
- `TELEGRAM_BOT_TOKEN` · `TELEGRAM_ALLOWED_USER_IDS`
- `SLACK_BOT_TOKEN` · `SLACK_APP_TOKEN`
- `HERMES_GITHUB_PAT` — GitHub PAT for self-update PRs

Volume `/data` — state lives at `/data/.hermes`.

## Critical gotchas

- **Volume path**: `/data/.hermes` (not `/root/.hermes`)
- **Zombie reaping**: `tini` is PID 1 — do not remove
- **Cookie auth**: HMAC secret regenerates on restart → redeploy invalidates sessions
- **PID file**: `start.sh` removes `gateway.pid` on boot; leftover file prevents Hermes from starting
- **Config merge**: `server.py` deep-merges into `config.yaml` / `.env` — never replace wholesale
- **Upgrading Hermes**: bump `HERMES_REF` in `infra/Dockerfile`, then rebuild (`/upgrade-hermes`)
