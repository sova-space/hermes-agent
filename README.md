# Sova — Personal AI Agent Family

> We are building a Telegram-based AI workspace system powered by the Hermes Agent framework in Python, where each domain-specific AI profile maps to one of the system's projects (finance, wishlist, …) and delegates its tasks to an autonomous AI worker that executes using tools, memory, and (optionally) subagents — not a chatbot, a profile-based AI execution environment.
>
> **Stack:** Python · Claude Code · Telegram · Railway

This is the *direction* the system is converging on, not a finished state — see [the gap between today and the target](#architecture) and [spec 014](specs/014-profile-router/spec.md) for what's left to build. Self-hosted on Railway.

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

Three bots today (Hermes, Finance, Wishlist), plus a fourth (Doer) slated for retirement — see [Architecture](#architecture). One monorepo, no shared state between independent services.

---

## Architecture

Profile-based dispatch — see [spec 014](specs/014-profile-router/spec.md) for the build-out:

```
                    Telegram (supergroup, topic-routed)
                                  │
                                  ▼
            ┌──────────────────────────────────────────────┐
            │   Hermes (orchestrator)                      │
            │   /profile <name>                            │
            │                                              │
            │   ├─ devops capability (BUILT IN — absorbed  │
            │   │  from Doer's generic GitHub loop;        │
            │   │  scoped to the selected profile's repo   │
            │   │  via the PROJECTS-style registry)        │
            │   │                                          │
            │   └─ domain conversation → routes to the     │
            │      profile-owning bot's assistant          │
            └──────────────────────┬───────────────────────┘
                                   │  (only for domain Q&A —
                                   │   devops stays in Hermes)
        ┌──────────────────────────┼──────────────────────────┐
        ▼                          ▼                          ▼
   finance bot's              wishlist bot's              <next> bot's
   assistant                  assistant                   assistant
   (own tools + memory,       (own tools + memory,        (own tools + memory,
    own DB — domain logic      own DB — domain logic       own DB — domain logic
    stays where the data is)   stays where the data is)    stays where the data is)
```

- **Devops intent** ("fix a bug in the finance bot") → handled by Hermes itself, via its built-in generic GitHub loop scoped to that profile's repo
- **Domain intent** ("what did I spend on food?") → routed to the profile-owning bot's own assistant, which holds the data and domain tools

Skills are declarative markdown (`SKILL.md`) — no Python modules. Each domain bot owns its own DB, Railway service, and bot token; domain logic stays where the data lives.

Request flow inside each domain API (e.g. Finance):

| Layer | Responsibility |
|-------|---------------|
| `routers/` | Parse HTTP, validate input, return response |
| `domains/` | Business logic, queries, sync, formatting |
| `core/` | Config, DB engine, logging setup |

---

## Services

### Sova Hermes — AI Orchestrator + Profile Router

Bot: `@pull_hermes_bot` · Service: `Hermes Agent` · Railway project: `hermes-main`

Handles conversations on Telegram. Routes by active profile: domain Q&A goes to the profile-owning bot's assistant; devops requests run through Hermes' own built-in GitHub loop, scoped to that profile's repo (see [Architecture](#architecture)).

**Skills:**
- `finance/SKILL.md` — routes money questions to the Finance REST API
- `project-context/` — tracks the active profile across conversations

### Sova Finance — Finance Bot

Bot: `@sova_finance_bot` · Service: `hermes-finance` · Railway project: `hermes-main`

Monobank sync, spending analytics, budget tracking — plus a conversational assistant for free-form money questions (`finance_api/domains/assistant/`). Full documentation: [`bots/finance/README.md`](bots/finance/README.md).

**Quick reference — bot commands:**

| Command | What it does |
|---------|-------------|
| `/balance` | Current balance for every synced account |
| `/stats [period] [mode]` | Spending by category. Periods: `this_month` `last_month` `last_7d` `last_30d` `last_90d` |
| `/budget` | Monthly limits vs current spending |
| `/sync` | Trigger Monobank sync immediately |

Or just ask in plain text — the conversational assistant answers free-form money questions directly.

### Sova Wishlist — Wishlist Bot

Bot: `@sova_wishlist_bot` · Service: `hermes-wishlist` · Railway project: `hermes-main`

Tracks wishlist items via Telegram, with AI-assisted item entry — describe what you want and the bot fills in the details.

---

## Project structure

```
.
├── server.py                     # Hermes admin server — manages + reverse-proxies the runtime
├── hermes/
│   ├── config/                   # SOUL.md, STYLE.md, channels.md, telegram.yaml, slack.yaml
│   ├── plugins/agent-silence/    # /profile command surface + chat-context plumbing
│   └── skills/
│       ├── finance/SKILL.md      # Calls Finance REST API to answer money questions
│       └── project-context/      # Tracks active project context
├── bots/
│   ├── finance/                  # @sova_finance_bot — own DB, Dockerfile, Railway service
│   │   └── finance_api/
│   │       ├── core/             # config, logging, db
│   │       ├── domains/
│   │       │   ├── accounts/     # Account model
│   │       │   ├── assistant/    # conversational assistant — tools + memory over finance domains
│   │       │   ├── bot/          # aiogram handlers, formatter, runner
│   │       │   ├── budgets/      # Budget model + queries
│   │       │   ├── insights/     # Analytics queries (spending, trend, transactions)
│   │       │   ├── sync/         # Monobank client, sync pipeline, MCC mapping
│   │       │   └── transactions/ # Transaction model + category mapping
│   │       ├── routers/          # REST endpoints
│   │       └── schemas.py        # Shared response schemas
│   ├── wishlist/                 # @sova_wishlist_bot — own DB, Dockerfile, Railway service
│   └── doer/                     # generic GitHub dev-loop — being absorbed into Hermes (spec 014)
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
docker build -f bots/finance/Dockerfile bots/finance/
```

| Service | Local URL |
|---------|-----------|
| Hermes admin | http://localhost:8080 |
| Finance API | http://localhost:8001 |
| Finance API docs | http://localhost:8001/docs |

### Deploy to Railway

One Railway project — `hermes-main` — hosts all services:

| Service | Name | Root directory |
|---------|------|---------------|
| Hermes orchestrator | `Hermes Agent` | repo root |
| Finance | `hermes-finance` | `bots/finance/` |
| Wishlist | `hermes-wishlist` | `bots/wishlist/` |
| Doer (devops, retiring — see [spec 014](specs/014-profile-router/spec.md)) | `hermes-doer` | `bots/doer/` |
| PostgreSQL | `Postgres` | — |

**Auto-deploy is active.** Push to `main` → Railway deploys only the affected service via watch patterns. No manual `railway up` needed.

Services communicate over **private networking** (`*.railway.internal`) using Railway reference variables — no public URLs in config.

Environment variables are set in Railway Variables only — never in the repo. See [`bots/finance/README.md`](bots/finance/README.md#environment-variables) for the full variable list.

---

## Development

### Logging

Each service uses [structlog](https://www.structlog.org/) to stdout. No file logging.

```bash
docker compose -f infra/docker-compose.yml logs -f finance
docker compose -f infra/docker-compose.yml logs -f hermes
```

On Railway: service → **Deployments** → active deployment → **Logs** tab.

### Tests

```bash
cd bots/finance
uv run pytest tests/ -v
```

Tests cover MCC category mapping, period math, and transaction categorization. All mocked — no real API calls.

### Lint & Format

Each `bots/<name>/` is an independent Python project — run lint from its own root:

```bash
# Hermes orchestrator (repo root)
uv run --dev ruff check .

# Finance
cd bots/finance && uv run ruff check finance_api/
```

After editing `pyproject.toml` in any project, run `uv lock` from that project's root.

---

## Contributing

1. Read [`CLAUDE.md`](CLAUDE.md) — repo rules, Railway topology, project conventions
2. Open an issue or start a discussion before building
3. Every feature needs a spec: `specs/NNN-feature-slug/spec.md` before any code
4. Branch names: `NNN-short-slug`. No direct pushes to `main`
5. Run lint before opening a PR: `uv run ruff check`

---

## License

MIT
