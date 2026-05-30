# hermes-agent

Personal AI agent running on Railway. Lives in a Telegram supergroup with dedicated topics per domain: delegate tasks in `#general`, get scheduled digests in `#projects`, query balances and spending in `#finance`. Syncs Monobank accounts hourly, tracks budgets, and proposes its own codebase improvements via GitHub PRs.

Built on the [NousResearch Hermes Agent](https://github.com/NousResearch/hermes-agent) runtime — configured, not forked.

## Services

| Service | Bot | What it does |
|---------|-----|--------------|
| `hermes-orchestrator` | `@sova_hermes_bot` | Conversations, routing, skills. Calls sub-agents over HTTP. |
| `agents/finance` | `@sova_finance_bot` | Monobank sync, spending analytics, budget tracking. |

One conversation on Telegram/Slack → Hermes routes → sub-agent answers.

```text
Telegram / Slack
      │
      ▼
hermes-orchestrator          NousResearch runtime + server.py
  hermes/skills/
    finance/SKILL.md ──HTTP──► agents/finance  FastAPI + PostgreSQL
                                               aiogram (@sova_finance_bot)
                                               Monobank sync (hourly)
```

Skills are declarative markdown (`SKILL.md`). Each sub-agent owns its own DB, Railway service, and bot token — no shared state between them.

## Table of Contents

- [Project structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Run locally](#run-locally)
- [Logging](#logging)
- [Tests](#tests)
- [Lint & Format](#lint--format)
- [Development setup](#development-setup)

## Project structure

```text
.
├── server.py                     # Hermes admin server — manages + reverse-proxies the runtime
├── hermes/
│   ├── config/                   # SOUL.md, STYLE.md, channels.md, telegram.yaml, slack.yaml
│   └── skills/
│       ├── finance/SKILL.md      # Calls finance REST API to answer money questions
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
│       │   ├── routers/          # REST endpoints called by hermes finance skill
│       │   └── schemas.py        # Shared response schemas
│       ├── alembic/              # DB migrations
│       └── tests/                # pytest unit tests
├── infra/
│   ├── Dockerfile                # Hermes image (build context: repo root)
│   ├── start.sh                  # Container entrypoint
│   ├── docker-compose.yml        # Local dev: all services + shared postgres
│   └── postgres-init/            # DB init scripts
├── specs/                        # Feature specs (spec.md per feature)
└── docs/
    └── constitution.md
```

### Architecture

```text
Telegram / Slack
      │
      ▼
Hermes runtime         (hermes-orchestrator — Railway service)
server.py              admin server + reverse proxy
hermes/skills/         finance skill ──► HTTP ──► finance REST API
                       project-context skill
      │ HTTP
      ▼
Finance API            (@sova_finance_bot — Railway service)
routers/               REST API  ◄── called by hermes finance skill
domains/bot/           aiogram   ◄── @sova_finance_bot Telegram commands
domains/sync/          APScheduler hourly Monobank sync
PostgreSQL             accounts, transactions, budgets
```

### Finance API layer

The request flow is always:

| Layer      | Responsibility                                         |
|------------|--------------------------------------------------------|
| `routers`  | Parse HTTP request, validate input, return response    |
| `domains`  | Business logic, queries, sync, formatting              |
| `core`     | Config, DB engine, logging setup                       |

Handlers are Telegram boundary only — no analytics logic inline. Queries take a `Session`, return plain dicts — no HTTP, no AI.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) with Compose plugin
- `infra/.env.finance.local` with real values (copy from `infra/.env.finance.local.example`)

## Run locally

```bash
# all services (hermes + finance + postgres)
docker compose -f infra/docker-compose.yml up

# hermes only
docker build -t hermes-agent .
docker run --rm -it -p 8080:8080 -e PORT=8080 -e ADMIN_PASSWORD=changeme -v hermes-data:/data hermes-agent

# finance only
docker build -f agents/finance/Dockerfile agents/finance/
```

## Logging

Both services use [structlog](https://www.structlog.org/) to stdout. No file logging.

```text
Request
  -> Handler  →  event logged with domain context
  -> structlog → stdout → Railway logs
```

Sample output:

```text
{"event": "scheduler_started",      "interval_hours": 1}
{"event": "telegram_bot_started"}
{"event": "sync.started",           "account_id": "abc123"}
{"event": "sync.completed",         "fetched": 42, "duration_ms": 380}
```

### Configuration

| Variable     | Default | Options                                          |
|--------------|---------|--------------------------------------------------|
| `LOG_LEVEL`  | `INFO`  | `DEBUG` · `INFO` · `WARNING` · `ERROR`           |
| `environment`| `local` | `local` (console format) · `production` (JSON)   |

### View logs

```bash
docker compose -f infra/docker-compose.yml logs -f finance   # finance logs
docker compose -f infra/docker-compose.yml logs -f hermes    # hermes logs
```

On Railway: service → **Deployments** → active deployment → **Logs** tab.

## Tests

Finance unit tests use `.env.test` (loaded automatically).

```bash
cd agents/finance
uv run pytest tests/ -v

# short output
uv run pytest tests/ --tb=short
```

Tests cover MCC category mapping, period math, and transaction categorization. All mocked — no real API calls.

## Lint & Format

Two independent Python projects — run from their own roots:

```bash
# hermes orchestrator (repo root)
uv run --dev ruff check .
uv run --dev ruff format .

# finance sub-agent
cd agents/finance
uv run ruff check finance_api/
uv run ruff format finance_api/
```

After editing `pyproject.toml` in either project, run `uv lock` from that project's root.

## Development setup

| Service        | Local                   | Production                                          |
|----------------|-------------------------|-----------------------------------------------------|
| Hermes admin   | http://localhost:8080   | Railway service URL                                 |
| Finance API    | http://localhost:8001   | https://finance-api-production-4d72.up.railway.app  |
| Finance docs   | http://localhost:8001/docs | https://finance-api-production-4d72.up.railway.app/docs |
| Finance health | http://localhost:8001/health | https://finance-api-production-4d72.up.railway.app/health |

### Deploy

Railway does **not** auto-deploy on push. After merging to `main`:

```bash
railway up --detach
```

Run from the correct service context (link with `railway link` first).
