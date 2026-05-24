# 001 — Railway Bootstrap: Document Existing Deployment

## Status
Config/documentation only — no code changes.

## What This Is

This spec documents the existing Railway deployment of Hermes Agent as it stands on
2026-05-25. The goal is a stable reference so any future change or redeploy can be
validated against a known-good baseline.

## Volume Path

The container sets `ENV HOME=/data` and `ENV HERMES_HOME=/data/.hermes` in the Dockerfile.
All persistent state lives under the Railway volume mounted at **`/data`** (not `/root/.hermes`,
which is the Hermes upstream default). If the volume is mounted elsewhere, set `HERMES_HOME`
accordingly.

## Required Environment Variables

Set these in the Railway service's "Variables" tab.

### Core (always required)

| Variable | Example value | Notes |
|---|---|---|
| `PORT` | `8080` | Railway injects this automatically |
| `ADMIN_PASSWORD` | `<your-password>` | If unset, a random one is printed to deploy logs |
| `ADMIN_USERNAME` | `admin` | Default is `admin`; override to taste |

### LLM Provider (set at least one)

| Variable | Notes |
|---|---|
| `OPENROUTER_API_KEY` | Recommended — gives access to many models via one key |
| `OPENAI_API_KEY` | Direct OpenAI access |
| `ANTHROPIC_API_KEY` | Direct Anthropic/Claude access |
| `DEEPSEEK_API_KEY` | DeepSeek models |

### Model Selection

| Variable | Example | Notes |
|---|---|---|
| `LLM_MODEL` | `openai/gpt-4o-mini` | Hermes model identifier (provider/model-name) |

### Telegram (messaging channel)

| Variable | Notes |
|---|---|
| `TELEGRAM_BOT_TOKEN` | From @BotFather — enables the Telegram channel |
| `TELEGRAM_ALLOWED_USER_IDS` | Comma-separated Telegram numeric user IDs that bypass the pairing step |

### GitHub / Vault integration

| Variable | Notes |
|---|---|
| `HERMES_GITHUB_PAT` | Fine-grained PAT scoped to `sova-claw/hermes-agent` only |
| `HERMES_VAULT_GIT_TOKEN` | Fine-grained PAT scoped to `sova-claw/hermes-vault` only |

> **Token separation**: per the constitution, these two tokens must have non-overlapping
> scopes. Currently they share a single `hermes-all` token — this must be remediated
> (see morning-summary.md).

## Volume Setup

1. In the Railway service, add a volume.
2. Mount point: `/data`
3. All Hermes state (config, sessions, logs, skills, memories) persists here across deploys.

## Architecture

```
Railway Container (tini PID 1)
└── start.sh
    ├── mkdir -p /data/.hermes/{cron,sessions,logs,...}
    ├── cp cli-config.yaml.example → /data/.hermes/config.yaml  (first boot only)
    ├── rm -f /data/.hermes/gateway.pid   (stale PID cleanup)
    └── exec python /app/server.py
        ├── Admin UI  → https://<railway-url>/
        ├── /health   → health check (no auth)
        └── /api/*    → config, status, logs, gateway, pairing
```

## What's Already Working (as of 2026-05-25)

- Docker image builds from `ghcr.io/astral-sh/uv:python3.12-bookworm-slim`
- Hermes pinned to `v2026.5.16`
- `tini` as PID 1 for zombie reaping
- React dashboard pre-built at image build time (`HERMES_TUI_DIR=/opt/hermes-agent/ui-tui`)
- Stale PID file removed on every boot
- Cookie-based auth (HMAC-signed, regenerates on redeploy — existing sessions invalidated)
- Admin dashboard accessible at the Railway-assigned URL
- Config deep-merged into volume on startup (preserves user customizations)
