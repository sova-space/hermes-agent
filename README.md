# hermes-agent

Nazar's personal AI agent running on Railway. Replies on Telegram and Slack, tracks finances via Monobank, proposes self-improvements via GitHub PRs.

Built on the [NousResearch Hermes Agent](https://github.com/NousResearch/hermes-agent) runtime — configured, not forked.

## Architecture

Two services, one repo, one PostgreSQL host:

```
Telegram / Slack
       │
       ▼
  Hermes runtime  (hermes-orchestrator Railway service)
  server.py           admin server + reverse proxy
  hermes/skills/      finance skill → HTTP → finance REST API
                      project-context skill
       │ HTTP
       ▼
  Finance API     (@sova_finance_bot Railway service)
  finance_api/        FastAPI REST API  ← called by hermes skill
  domains/bot/        aiogram bot       ← @sova_finance_bot Telegram commands
  domains/sync/       Monobank sync     ← APScheduler hourly
  PostgreSQL          accounts, transactions, budgets
```

The hermes skill (`hermes/skills/finance/SKILL.md`) is the integration point. Hermes resolves finance questions by calling the REST API; `@sova_finance_bot` handles direct bot commands in the `#finance` Telegram topic.

## Services

| Service | Railway root | Bot |
|---------|-------------|-----|
| hermes-orchestrator | `/` (repo root) | `@sova_hermes_bot` |
| hermes-finance | `agents/finance/` | `@sova_finance_bot` |

Shared PostgreSQL: `hermes-db`. Finance uses the `finance` database.

## Repo structure

```
server.py                   # Hermes admin server (single file)
hermes/
  config/                   # SOUL.md, STYLE.md, channels.md, telegram.yaml, slack.yaml
  skills/
    finance/SKILL.md        # Calls agents/finance REST API
    project-context/SKILL.md
infra/
  Dockerfile                # Builds hermes image (build context: repo root)
  start.sh                  # Container entrypoint
  docker-compose.yml        # Local dev: all services + shared postgres
agents/
  finance/                  # @sova_finance_bot — separate Railway service
    finance_api/            # FastAPI + aiogram + APScheduler
    alembic/                # DB migrations
specs/                      # Feature specs (spec.md only — one per feature)
docs/
  constitution.md
```

## Development

Docker-only. No local virtualenvs.

```bash
# Build hermes
docker build -t hermes-agent .

# Run hermes locally
docker run --rm -it -p 8080:8080 -e PORT=8080 -e ADMIN_PASSWORD=changeme -v hermes-data:/data hermes-agent

# Build finance
docker build -f agents/finance/Dockerfile agents/finance/

# All services (local dev)
docker compose -f infra/docker-compose.yml up
```

## Python projects

Two independent projects — never mix their commands:

| Project | Root | Commands |
|---------|------|----------|
| Hermes orchestrator | repo root | `uv run --dev ruff check .` |
| Finance agent | `agents/finance/` | `uv run ruff check finance_api/` · `uv run pytest tests/` |

## Key env vars

| Variable | Service | Notes |
|----------|---------|-------|
| `ADMIN_PASSWORD` | hermes | Dashboard auth |
| `LLM_MODEL` | hermes | e.g. `openai/gpt-4o-mini` |
| `OPENROUTER_API_KEY` | hermes | LLM provider |
| `TELEGRAM_BOT_TOKEN` | hermes | `@sova_hermes_bot` |
| `TELEGRAM_ALLOWED_USER_IDS` | hermes | Comma-separated IDs |
| `SLACK_BOT_TOKEN` / `SLACK_APP_TOKEN` | hermes | Socket Mode |
| `HERMES_GITHUB_PAT` | hermes | Self-update PRs (scoped to this repo only) |
| `DATABASE_URL` | finance | `postgresql+psycopg://…/finance` |
| `TELEGRAM_BOT_TOKEN` | finance | `@sova_finance_bot` |
| `MONOBANK_TOKEN` | finance | Personal token |
| `FINANCE_API_URL` | hermes | URL of the finance REST API |

All secrets in Railway Variables — never committed.

## Adding a feature

1. Create branch `NNN-short-slug`
2. Write `specs/NNN-feature-slug/spec.md` (what, acceptance criteria, open questions)
3. Implement → PR → merge
