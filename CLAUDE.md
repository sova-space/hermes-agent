# CLAUDE.md

Hermes is Nazar's personal AI agent — Telegram, finance tracking, self-improvement via GitHub PRs.
Bot: `@sovaa_hermes_bot`

## Rules
- Skills = `hermes/skills/<name>/SKILL.md` (markdown only, companion script for code)
- Python 3.11+, type hints, `ruff check` + `ruff format` before merge

## Repo structure

```
server.py / hermes/        — Hermes orchestrator + plugins
infra/                     — Dockerfile, start.sh, docker-compose.yml
bots/finance/              — @sova_finance_bot (FastAPI + aiogram + APScheduler)
bots/wishlist/             — @sova_wishlist_bot (FastAPI + PTB)
specs/                     — Feature specs
```

Each `bots/<name>/` has its own `Dockerfile`, `railway.toml`, `pyproject.toml`, `uv.lock`. Never mix uv/pytest commands between projects.

## Railway topology

Project: `hermes-main` · `3d73dc58` · environment `production` · `a2a88403`

| Service | ID | Path |
|---|---|---|
| Hermes Agent | `8d1fc2f6` | repo root |
| hermes-finance | `9bc27c48` | `bots/finance/` |
| hermes-wishlist | `7764e517` | `bots/wishlist/` |
| Postgres | `b6daf7a2` | — |

DB names: `railway` (hermes) · `finance` · `wishlist`. Ref vars: `${{Postgres.DATABASE_URL}}` etc.
Auto-deploy on `main` push per watch pattern. See `@finance-devops` / `@wishlist-devops` for link commands.

## Profile + mode routing

Hermes has three profiles, one per project: `finance` / `wishlist` / `hermes`.

- `/profile <name>` — switch the active profile for this chat
- `/mode client` — plain messages go to that profile's domain assistant (Q&A)
- `/mode dev` — plain messages run as devops tasks against that profile's GitHub repo

The devops loop (`/mode dev`) runs in-process via `hermes/plugins/agent-silence/devops.py` — no separate service. It uses GitHub + OpenRouter (Haiku model by default) and posts results to `#projects`.

## Bot command sync

`commands.py` → `BOT_COMMANDS` + `setup_bot(bot)` → `GET /bot/commands` (Hermes reads at runtime). Add commands in `commands.py` only.

## Project slugs (single source of truth)

Slugs must be identical everywhere or routing breaks (`finance` / `wishlist` / `hermes`):

- **Source of truth**: `hermes/plugins/agent-silence/devops.py` (`PROJECTS` dict) — drives `/profile <name>` and devops dispatch.
- **Mirror**: `hermes/skills/project-context/` (`KNOWN_PROJECTS` in `project.py` + `SKILL.md`) — used only for self-tagging Hermes' own cron output as `[<project>]`.

## Hermes gotchas

- Volume: `/data/.hermes` (not `/root/.hermes`)
- `tini` is PID 1 — do not remove
- `start.sh` removes `gateway.pid` on boot
- Upgrade: bump `HERMES_REF` in `infra/Dockerfile` → `/upgrade-hermes`

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
