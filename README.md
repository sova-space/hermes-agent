# Hermes Agent — Railway Template

Deploy [Hermes Agent](https://github.com/NousResearch/hermes-agent) on [Railway](https://railway.app) with a web-based admin dashboard for configuration, gateway management, and user pairing.

[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/deploy/hermes-agent-ai?referralCode=QXdhdr&utm_medium=integration&utm_source=template&utm_campaign=generic)

Hermes Agent is an autonomous AI agent by [Nous Research](https://nousresearch.com/) that lives on your server, connects to your messaging channels (Telegram, Discord, Slack, etc.), and gets more capable the longer it runs. This repo wraps Hermes in a lightweight admin server and packages it for one-click Railway deployment.

## Deploy to Railway

1. Click **Deploy on Railway** above
2. Set `ADMIN_PASSWORD` (or a random one is generated and printed to logs)
3. Attach a **volume** mounted at `/data` — all Hermes state persists here
4. Set at least one LLM provider key and `LLM_MODEL` (see env vars table below)
5. Open your Railway URL, log in with `admin` / your password
6. Start the gateway from the dashboard

### Required Environment Variables

| Variable | Notes |
|---|---|
| `PORT` | Set automatically by Railway |
| `ADMIN_PASSWORD` | Auto-generated if unset (check deploy logs) |
| `ADMIN_USERNAME` | Default `admin` |
| `LLM_MODEL` | e.g. `openai/gpt-4o-mini`, `claude-sonnet-4-5` |
| `OPENROUTER_API_KEY` | Recommended — access to many models via one key |
| `OPENAI_API_KEY` | Direct OpenAI (alternative to OpenRouter) |
| `ANTHROPIC_API_KEY` | Direct Anthropic/Claude (alternative) |
| `TELEGRAM_BOT_TOKEN` | From @BotFather — enables Telegram channel |
| `TELEGRAM_ALLOWED_USER_IDS` | Comma-separated Telegram user IDs that skip pairing |
| `HERMES_GITHUB_PAT` | PAT for `sova-claw/hermes-agent` — enables GitHub MCP |
| `RAILWAY_API_TOKEN` | **Required** — Railway API token for MCP server. Get it at [railway.app/account](https://railway.app/account) → **Create API Token**. Enables agent to trigger deploys, check service status, and manage Railway resources. |

### Railway API Token Setup

1. Go to [railway.app/account](https://railway.app/account)
2. Click **Create API Token**
3. Copy the token (format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)
4. Add it as `RAILWAY_API_TOKEN` in Railway service environment variables
5. The agent auto-configures the Railway MCP server on startup

## Adding a New Feature

This repo uses a lightweight spec-first loop:

1. Create a branch: `feature/<name>` for new work, `fix/<name>` for bug fixes
2. Write `specs/<NNN>-<slug>/spec.md`, `plan.md`, `tasks.md`
3. Implement the feature (code, skills, config snippets)
4. PR → merge → update `main`

All designed features are documented under `specs/`:

- [`specs/001-railway-bootstrap/`](specs/001-railway-bootstrap/) — Railway env vars, volume setup, verification checklist
- [`specs/004-self-update-loop/`](specs/004-self-update-loop/) — GitHub MCP config + SOUL.md agent identity

Agent-proposed changes use branches named `hermes-proposal/<slug>` and always go through a PR (see `skills/SOUL.md`).

## Running Locally

```bash
docker build -t hermes-agent .
docker run --rm -it -p 8080:8080 -e PORT=8080 -e ADMIN_PASSWORD=changeme -v hermes-data:/data hermes-agent
```

Open `http://localhost:8080` and log in with `admin` / `changeme`.

## Credits

- [Hermes Agent](https://github.com/NousResearch/hermes-agent) by [Nous Research](https://nousresearch.com/)
- UI inspired by [OpenClaw](https://github.com/praveen-ks-2001/openclaw-railway) admin template
