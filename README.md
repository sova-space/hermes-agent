# Sova — Personal AI Agent Family

> Personal AI assistant living in Telegram. Conversations routed by Hermes, finances tracked by Sova Finance. Self-hosted on Railway.

Built on the [NousResearch Hermes Agent](https://github.com/NousResearch/hermes-agent) runtime — configured, not forked.

## Table of Contents

- [What is Sova?](#what-is-sova)
- [Architecture](#architecture)
- [Services](#services)
  - [Sova Hermes — AI Orchestrator](#sova-hermes--ai-orchestrator)
  - [Sova Finance — Finance Bot](#sova-finance--finance-bot)
- [Project structure](#project-structure)
- [Self-Hosting](#self-hosting)
  - [Prerequisites](#prerequisites)
  - [Run locally](#run-locally)
  - [Deploy to Railway](#deploy-to-railway)
- [Development](#development)
  - [Logging](#logging)
  - [Tests](#tests)
  - [Lint & Format](#lint--format)
- [Contributing](#contributing)
- [License](#license)

---

## What is Sova?

Sova is a personal AI agent ecosystem for one user. It lives in a Telegram supergroup with dedicated topics per domain:

| Topic | Purpose |
|-------|---------|
| `#general` | Delegate tasks, ask questions |
| `#projects` | Scheduled digests, status updates |
| `#finance` | Balance checks, spending queries |

Two bots, one monorepo, no shared state between services.

---

## Architecture

```
Telegram / Slack
      │
      ▼
Sova Hermes (@sova_hermes_bot)        NousResearch runtime + server.py
  hermes/skills/
    finance/SKILL.md  ──HTTP──►  Sova Finance (@sova_finance_bot)
    project-context/                   FastAPI + PostgreSQL
                                       aiogram bot
                                       Monobank sync (hourly, APScheduler)
```

Skills are declarative markdown (`SKILL.md`) — no Python modules. Each sub-agent owns its own DB, Railway service, and bot token.

Request flow inside Finance API:

| Layer | Responsibility |
|-------|---------------|
| `routers/` | Parse HTTP, validate input, return response |
| `domains/` | Business logic, queries, sync, formatting |
| `core/` | Config, DB engine, logging setup |

---

## Services

### Sova Hermes — AI Orchestrator

Bot: `@sova_hermes_bot` · Service: `hermes-orchestrator` · Railway project: `hermes-main`

Handles conversations on Telegram and Slack. Routes user intent to skills. Proposes its own codebase improvements via GitHub PRs.

**Skills:**
- `finance/SKILL.md` — routes money questions to the Finance REST API
- `project-context/` — tracks active project context across conversations

### Sova Finance — Finance Bot

Bot: `@sova_finance_bot` · Service: `finance-api` · Railway project: `finance-agent`

Monobank sync, spending analytics, budget tracking. Full documentation: [`agents/finance/README.md`](agents/finance/README.md).

**Quick reference — bot commands:**

| Command | What it does |
|---------|-------------|
| `/balance` | Current balance for every synced account |
| `/stats [period] [mode]` | Spending by category. Periods: `this_month` `last_month` `last_7d` `last_30d` `last_90d` |
| `/budget` | Monthly limits vs current spending |
| `/sync` | Trigger Monobank sync immediately |

See [`agents/finance/README.md`](agents/finance/README.md) for the full REST API reference, spending categories, roadmap, and known bugs.

---

## Project structure

```
.
├── server.py                     # Hermes admin server — manages + reverse-proxies the runtime
├── hermes/
│   ├── config/                   # SOUL.md, STYLE.md, channels.md, telegram.yaml, slack.yaml
│   └── skills/
│       ├── finance/SKILL.md      # Calls Finance REST API to answer money questions
│       └── project-context/      # Tracks active project context
├── agents/
│   └── finance/                  # @sova_finance_bot — separate Railway service
│       ├── finance_api/
│       │   ├── core/             # config, logging, db
│       │   ├── domains/
│       │   │   ├── accounts/     # Account model
│       │   │   ├── bot/          # aiogram handlers, formatter, runner
│       │   │   ├── budgets/      # Budget model + queries
│       │   │   ├── insights/     # Analytics queries (spending, trend, transactions)
│       │   │   ├── sync/         # Monobank client, sync pipeline, MCC mapping
│       │   │   └── transactions/ # Transaction model + category mapping
│       │   ├── routers/          # REST endpoints called by Hermes finance skill
│       │   └── schemas.py        # Shared response schemas
│       ├── alembic/              # DB migrations
│       └── tests/                # pytest unit tests
├── infra/
│   ├── Dockerfile                # Hermes image (build context: repo root)
│   ├── start.sh                  # Container entrypoint
│   ├── docker-compose.yml        # Local dev: all services + shared postgres
│   └── postgres-init/            # DB init scripts
├── docs/                         # GitHub Pages landing page
└── specs/                        # Feature specs (spec.md per feature, written before code)
```

---

## Self-Hosting

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) with Compose plugin
- A [Railway](https://railway.app) account
- Telegram bot tokens (from [@BotFather](https://t.me/BotFather))
- Monobank personal token (from [monobank.ua/api](https://monobank.ua/api))
- `infra/.env.finance.local` filled in (copy from `infra/.env.finance.local.example`)

### Run locally

```bash
# All services (Hermes + Finance + PostgreSQL)
docker compose -f infra/docker-compose.yml up

# Hermes only
docker build -t hermes-agent .
docker run --rm -it -p 8080:8080 -e PORT=8080 -e ADMIN_PASSWORD=changeme -v hermes-data:/data hermes-agent

# Finance only
docker build -f agents/finance/Dockerfile agents/finance/
```

| Service | Local URL |
|---------|-----------|
| Hermes admin | http://localhost:8080 |
| Finance API | http://localhost:8001 |
| Finance API docs | http://localhost:8001/docs |

### Deploy to Railway

Two separate Railway projects, both served from this monorepo:

| Component | Railway Project | Project ID |
|-----------|----------------|------------|
| Hermes orchestrator | `hermes-main` | `3d73dc58-1201-4258-bc1d-1f9c24333032` |
| Finance sub-agent | `finance-agent` | `186cf9f1-f88f-4b73-b286-a055e107cc9d` |

Railway does **not** auto-deploy on git push. After merging to `main`:

```bash
# Hermes orchestrator — from repo root
railway up --detach

# Finance sub-agent — from agents/finance/
cd agents/finance
railway link --project 186cf9f1-f88f-4b73-b286-a055e107cc9d --service b6cb492f-9100-4330-82db-8afd95d6fe91
railway up --detach
```

Environment variables are set in Railway Variables only — never in the repo. See [`agents/finance/README.md`](agents/finance/README.md#environment-variables) for the full variable list.

---

## Development

### Logging

Both services use [structlog](https://www.structlog.org/) to stdout. No file logging.

```bash
docker compose -f infra/docker-compose.yml logs -f finance
docker compose -f infra/docker-compose.yml logs -f hermes
```

On Railway: service → **Deployments** → active deployment → **Logs** tab.

### Tests

```bash
cd agents/finance
uv run pytest tests/ -v
```

Tests cover MCC category mapping, period math, and transaction categorization. All mocked — no real API calls.

### Lint & Format

Two independent Python projects — run from their own roots:

```bash
# Hermes orchestrator (repo root)
uv run --dev ruff check .

# Finance sub-agent
cd agents/finance && uv run ruff check finance_api/
```

After editing `pyproject.toml` in either project, run `uv lock` from that project's root.

---

## Contributing

1. Read [`docs/constitution.md`](docs/constitution.md) — project values and constraints
2. Open an issue or start a discussion before building
3. Every feature needs a spec: `specs/NNN-feature-slug/spec.md` before any code
4. Branch names: `NNN-short-slug`. No direct pushes to `main`
5. Run lint before opening a PR: `uv run ruff check`

---

## License

MIT
