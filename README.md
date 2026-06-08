# Sova — Personal AI Agent Family

A Telegram-based AI workspace for one user. Profile-based routing: pick a project, choose a mode, talk naturally.

**Stack:** Python · Claude · Telegram · Railway · NousResearch Hermes runtime

---

## How it works

One supergroup, topic-routed:

| Topic | Purpose |
|-------|---------|
| `#general` | Conversations, task delegation |
| `#projects` | Devops results, scheduled digests |
| `#finance` | Balance, spending, budgets |

Three services, one monorepo. Each service owns its own DB, Dockerfile, and bot token — no shared state.

---

## Architecture

```
Telegram supergroup
        │
        ▼
┌───────────────────────────────────────────┐
│  @sovaa_hermes_bot  (orchestrator)        │
│                                           │
│  /profile finance|wishlist|hermes         │
│  /mode client|dev                         │
│                                           │
│  client mode → routes to domain bot's    │
│                assistant (Q&A)            │
│                                           │
│  dev mode    → runs GitHub agent loop    │
│                against profile's repo    │
│                posts result to #projects  │
└──────────────┬────────────────────────────┘
               │ client mode only
       ┌───────┴────────┐
       ▼                ▼
 @sova_finance_bot   @sova_wishlist_bot
 (own DB + tools)    (own DB + tools)
```

- **`/mode client`** — plain messages go to the profile's domain assistant
- **`/mode dev`** — plain messages are devops tasks; the GitHub loop reads/writes code and opens a PR
- Devops runs in-process inside Hermes (`hermes/plugins/agent-silence/devops.py`) — no separate worker service

---

## Services

| Service | Bot | Railway service | Path |
|---------|-----|----------------|------|
| Hermes orchestrator | `@sovaa_hermes_bot` | `Hermes Agent` | repo root |
| Finance | `@sova_finance_bot` | `hermes-finance` | `bots/finance/` |
| Wishlist | `@sova_wishlist_bot` | `hermes-wishlist` | `bots/wishlist/` |
| PostgreSQL | — | `Postgres` | — |

Railway project: `hermes-main`. All services communicate over private networking (`*.railway.internal`).

Auto-deploy: push to `main` → Railway deploys only affected services via watch patterns.

---

## Project structure

```
server.py                       # Hermes admin server + reverse proxy
hermes/
  config/                       # SOUL.md, STYLE.md, channels.md, telegram.yaml
  plugins/
    agent-silence/              # /profile + /mode routing; in-process devops loop
      devops.py                 # GitHub agent loop (PROJECTS registry here)
      commands.py               # /profile, /mode handlers
      doer.py                   # session state, domain Q&A routing
  skills/
    finance/SKILL.md            # Routes money questions to Finance REST API
    project-context/            # Self-tags Hermes cron output with active project
bots/
  finance/                      # @sova_finance_bot — FastAPI + aiogram + APScheduler
    finance_api/
      domains/                  # assistant/, insights/, sync/, accounts/, transactions/
      routers/                  # REST endpoints called by hermes finance skill
  wishlist/                     # @sova_wishlist_bot — FastAPI + PTB
infra/
  Dockerfile                    # Hermes image (build context: repo root)
  start.sh                      # Container entrypoint
  docker-compose.yml            # Local dev: all services + postgres
specs/                          # Feature specs (spec.md written before code)
```

---

## Running locally

```bash
# All services
docker compose -f infra/docker-compose.yml up

# Hermes only
docker build -t hermes-agent -f infra/Dockerfile .
docker run --rm -p 8080:8080 -e PORT=8080 -e ADMIN_PASSWORD=dev hermes-agent

# Finance only
docker build -f bots/finance/Dockerfile bots/finance/
```

Copy `infra/.env.finance.local.example` → `infra/.env.finance.local` and fill in secrets before starting Finance locally.

---

## Development

**Lint** (run from each project root — never mix):

```bash
uv run --dev ruff check .          # repo root (Hermes)
cd bots/finance && uv run ruff check finance_api/
cd bots/wishlist && uv run ruff check wishlist_api/
```

**Tests:**

```bash
cd bots/finance && uv run pytest tests/ -v
```

**Logs** — Railway: service → Deployments → active deployment → Logs. Locally: `docker compose logs -f <service>`.

**Knowledge graphs** (AST-only, no LLM cost):

```bash
graphify update .              # root (hermes/)
graphify update bots/finance
graphify update bots/wishlist
```

Use `graphify query "<question>"` in any AI session instead of grepping files.

---

## License

MIT
