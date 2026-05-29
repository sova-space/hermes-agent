# Spec 008: Finance–Hermes Monorepo Integration

## Problem

`hermes-finance` (the `@sova_finance_bot` Telegram bot + REST API) lives in a separate GitHub repo (`sova-claw/hermes-finance`). As the agent ecosystem grows (finance, travel, projects, …), managing many separate repos becomes friction: cross-cutting changes, shared infra, and deployment config are scattered.

## Solution

Consolidate `hermes-finance` into this repo as `agents/finance/`. Each agent lives under `agents/<name>/`, is built as its own Docker image, and deploys as a separate Railway service — but all share one git history, one CI, and one README.

The PostgreSQL database follows the same pattern: one shared Railway PostgreSQL service (`hermes-db`), one database per agent (`finance`, `travel`, …). Connection strings differ only in the database name.

## Architecture

```
hermes-agent/  (this repo)
├── server.py / hermes/          — sova_hermes_bot orchestrator
├── infra/docker-compose.yml     — local dev for all services + shared DB
└── agents/
    └── finance/                 — @sova_finance_bot (moved from sova-claw/hermes-finance)
        ├── Dockerfile
        ├── railway.toml
        ├── finance_api/
        └── alembic/
```

Future agents added as `agents/travel/`, `agents/projects/`, etc.

## Telegram bots

| Bot | Role |
|-----|------|
| `@sova_hermes_bot` | Main orchestrator — conversational AI, delegates via finance skill |
| `@sova_finance_bot` | Finance sub-agent — direct Monobank queries, budgets, sync |

Both coexist. The finance skill in hermes already calls the finance REST API; no skill changes needed.

## Acceptance criteria

- [ ] `agents/finance/` exists with full hermes-finance codebase
- [ ] `docker build -f agents/finance/Dockerfile agents/finance/` succeeds
- [ ] `docker build -f infra/Dockerfile .` still succeeds (hermes image unaffected)
- [ ] `docker compose -f infra/docker-compose.yml up` starts hermes + finance + postgres
- [ ] `CLAUDE.md` documents the monorepo structure and shared-DB pattern
- [ ] Railway finance service updated to root directory `agents/finance` (manual step)
- [ ] `sova-claw/hermes-finance` repo archived after Railway is confirmed working

## Open questions

- None for this phase.

## Out of scope

- Sub-agent delegation protocol (future spec)
- Travel or other agents (future)
- Merging finance into hermes runtime (finance remains its own Railway service)
