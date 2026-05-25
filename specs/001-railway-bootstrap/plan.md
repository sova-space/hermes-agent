# 001 — Plan: Railway Bootstrap Verification

## Overview

No code is written for this feature. The plan is a verification checklist for the user
to run after the first Railway deploy.

## Constitution Check

This feature is config/documentation only. No code paths, no secrets committed.
Complies with Principles I, IV, VII.

## Verification Checklist

### 1. Railway Service Health

- [ ] Railway deploy completes without build errors
- [ ] `/health` endpoint returns `200 OK`
- [ ] Admin dashboard loads at the Railway URL (no auth loop)
- [ ] Login with `admin` / `$ADMIN_PASSWORD` succeeds

### 2. Volume Persistence

- [ ] Volume is attached and mounted at `/data`
- [ ] After a manual redeploy: previously configured API keys and model are still set
- [ ] Gateway state survives restart (no "PID file race" errors in logs)
- [ ] `/data/.hermes/config.yaml` exists and is not blank

### 3. Telegram Channel

- [ ] `TELEGRAM_BOT_TOKEN` set in Railway variables
- [ ] Gateway started from admin dashboard
- [ ] Send a message to the bot → pairing request appears in admin under **Users**
- [ ] Approve the request → bot replies to your message
- [ ] Redeploy service → bot still replies (session persists from volume)

### 4. LLM Provider

- [ ] At least one provider key set and model configured
- [ ] Gateway logs show no "no LLM provider" errors
- [ ] Ask the bot a question → it responds (proves end-to-end LLM connectivity)

### 5. Token Separation (deferred — requires new tokens)

- [ ] `HERMES_GITHUB_PAT` updated to a new token scoped only to `sova-claw/hermes-agent`
- [ ] `HERMES_VAULT_GIT_TOKEN` updated to a new token scoped only to `sova-claw/hermes-vault`
- [ ] Old `hermes-all` token revoked on GitHub

## Config Snippet: Minimal Working config.yaml

The dashboard sets this automatically, but for reference the minimal manual config is:

```yaml
model: openrouter/openai/gpt-4o-mini   # adjust to your provider/model
```

All other config (channels, MCP servers, skills) is layered on top via the dashboard.
