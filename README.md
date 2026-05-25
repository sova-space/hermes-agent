# Hermes Agent — Railway Template

Deploy [Hermes Agent](https://github.com/NousResearch/hermes-agent) on [Railway](https://railway.app) with a web-based admin dashboard for configuration, gateway management, and user pairing.

[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/deploy/hermes-agent-ai?referralCode=QXdhdr&utm_medium=integration&utm_source=template&utm_campaign=generic)

Hermes Agent is an autonomous AI agent by [Nous Research](https://nousresearch.com/) that lives on your server, connects to your messaging channels (Telegram, Discord, Slack, etc.), and gets more capable the longer it runs. This repo wraps Hermes in a lightweight admin server and packages it for one-click Railway deployment.

## Two-Repo Structure

| Repo | Purpose |
|---|---|
| [`sova-claw/hermes-agent`](https://github.com/sova-claw/hermes-agent) | Docker image, admin server, skills, specs — the code you deploy |
| [`sova-claw/hermes-vault`](https://github.com/sova-claw/hermes-vault) | Private Obsidian-format note vault — the agent reads and writes here |

The two repos are separate so the vault (which may contain personal notes) stays private and isolated from the deployment codebase. The agent accesses the vault at runtime via a dedicated GitHub PAT (`HERMES_VAULT_GIT_TOKEN`) that has no access to the deployment repo.

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
| `HERMES_VAULT_GIT_TOKEN` | PAT for `sova-claw/hermes-vault` — enables vault skill |
| `HERMES_VAULT_ALLOW_DIRS` | Optional; default `agent-inbox,daily` |

## Adding a New Feature

This repo uses a lightweight Spec Kit loop:

1. Create a branch: `feature/<name>` for new work, `fix/<name>` for bug fixes
2. Write `specs/<NNN>-<slug>/spec.md`, `plan.md`, `tasks.md`
3. Implement the feature (code, skills, config snippets)
4. PR → merge → update `main`

All designed features are documented under `specs/`:

- [`specs/001-railway-bootstrap/`](specs/001-railway-bootstrap/) — Railway env vars, volume setup, verification checklist
- [`specs/002-notion-mcp/`](specs/002-notion-mcp/) — Notion MCP OAuth flow and config
- [`specs/003-obsidian-skill/`](specs/003-obsidian-skill/) — Obsidian vault skill (vault.py + SKILL.md)
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
