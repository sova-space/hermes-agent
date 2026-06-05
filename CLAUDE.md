# CLAUDE.md

Hermes is Nazar's personal AI agent — replies on Telegram and Slack, tracks finances, and proposes self-improvements via GitHub PRs. Runs on Railway using the Nous Research Hermes Agent runtime.

## Rules

- **Spec-first.** Write `specs/NNN-feature-slug/spec.md` before any code.
- **One feature, one branch, one PR.** Branch names: `NNN-short-slug`. No direct pushes to `main`. PRs auto-merge once approved.
- **Secrets never in the repo.** All tokens/keys in Railway Variables only.
- **MCP over custom code.** Use MCP servers for external integrations; Python only when no MCP exists.
- **Python quality.** Target Python 3.11+. All function signatures must have type hints. Pass `ruff check` + `ruff format` before merge.

## Repo structure

```
server.py                  # Hermes admin server
hermes/
  config/SOUL.md           # Agent identity (seeded to /data/.hermes/ on first boot)
  skills/finance/          # Finance skill — calls bots/finance REST API
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
| Finance sub-agent   | `bots/finance/` | `uv run ruff check finance_api/` · `uv run pytest tests/`  |

## Sub-agents

Each `bots/<name>/` has its own `Dockerfile`, `railway.toml`, `pyproject.toml`. Deployed as a separate Railway service (Root Directory = `bots/<name>/`). One PostgreSQL DB per agent on the shared `hermes-db` service.

```bash
# Build finance locally
docker build -f bots/finance/Dockerfile bots/finance/
```

### Bot command sync pattern

Every agent with a Telegram bot **must** follow this pattern to stay in sync with Hermes:

1. **`domains/bot/commands.py`** — single source of truth. Define `BOT_COMMANDS: list[BotCommand]` and a `setup_bot(bot)` function that calls all startup steps (register commands, set menu button, etc.). Add new startup actions here only.
2. **`routers/miniapp.py`** — expose `GET /bot/commands` returning `[{command, description}]` from `BOT_COMMANDS`.
3. **`composition.py` lifespan** — call `await setup_bot(bot_app.bot)` explicitly after `bot_app.initialize()`. No `post_init` callbacks.
4. **Hermes skill** — fetch `GET /bot/commands` at runtime to know which commands are owned by the agent bot. Never hardcode the list in SKILL.md.

**To add a command**: edit `BOT_COMMANDS` in `commands.py` only. Everything else stays in sync automatically.

## Railway Deployment

One Railway project — `hermes-main` — hosts all services from the same monorepo (`sova-space/hermes-agent`):

| Component | Service name | Service ID | Root directory |
|---|---|---|---|
| Hermes orchestrator | `Hermes Agent` | `8d1fc2f6-031b-4527-9a7d-3e78316d1180` | repo root |
| Finance sub-agent | `hermes-finance` | `9bc27c48-c35d-4dcf-9f4e-ba3c73e1ed96` | `bots/finance` |
| Wishlist bot | `hermes-wishlist` | `7764e517-0cc2-4378-894f-d4d82570339d` | `bots/wishlist` |
| Shared DB | `Postgres` | `b6daf7a2-de33-4767-a78b-e4e4d7424d58` | — |

Project: `hermes-main` · ID: `3d73dc58-1201-4258-bc1d-1f9c24333032` · Environment: `production` (`a2a88403-f2b1-4a18-a44d-3b808d07bcb1`)

Auto-deploy is active (Railway dashboard, branch: `main`). Watch patterns per service:
- Hermes Agent: `hermes/**`, `infra/**`, `server.py`, `railway.toml`
- hermes-finance: `bots/finance/**`
- hermes-wishlist: `bots/wishlist/**`

```bash
# Link to Hermes orchestrator (from repo root)
railway link --project 3d73dc58-1201-4258-bc1d-1f9c24333032 --service 8d1fc2f6-031b-4527-9a7d-3e78316d1180

# Link to Finance API (from bots/finance/)
railway link --project 3d73dc58-1201-4258-bc1d-1f9c24333032 --service 9bc27c48-c35d-4dcf-9f4e-ba3c73e1ed96

# Link to Wishlist bot (from bots/wishlist/)
railway link --project 3d73dc58-1201-4258-bc1d-1f9c24333032 --service 7764e517-0cc2-4378-894f-d4d82570339d
```

Postgres databases: `railway` (default), `finance` (hermes-finance), `wishlist` (hermes-wishlist). Reference vars: `${{Postgres.DATABASE_URL}}`, `${{Postgres.FINANCE_DATABASE_URL}}`, `${{Postgres.WISHLIST_DATABASE_URL}}`.

- Do NOT use `sova-space/hermes-finance` — that repo is stale
- Do NOT create new Railway services unless adding a genuinely new sub-agent
- The old `finance-agent` project (`186cf9f1`) has been decommissioned

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
