# CLAUDE.md

Hermes is Nazar's personal AI agent — Telegram, finance tracking, self-improvement via GitHub PRs.

## Rules
- Skills = `hermes/skills/<name>/SKILL.md` (markdown only, companion script for code)
- Python 3.11+, type hints, `ruff check` + `ruff format` before merge

## Repo structure

```
server.py / hermes/        — Hermes orchestrator
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
| hermes-doer | (see Railway) | `bots/doer/` |
| Postgres | `b6daf7a2` | — |

DB names: `railway` (hermes) · `finance` · `wishlist`. Ref vars: `${{Postgres.DATABASE_URL}}` etc.
Auto-deploy on `main` push per watch pattern. See `@finance-devops` / `@wishlist-devops` for link commands.

## Bot command sync

`commands.py` → `BOT_COMMANDS` + `setup_bot(bot)` → `GET /bot/commands` (Hermes reads at runtime). Add commands in `commands.py` only.

## Hermes gotchas

- Volume: `/data/.hermes` (not `/root/.hermes`)
- `tini` is PID 1 — do not remove
- `start.sh` removes `gateway.pid` on boot
- Upgrade: bump `HERMES_REF` in `infra/Dockerfile` → `/upgrade-hermes`
