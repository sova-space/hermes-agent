# Spec 005: Multi-target deployment (Oracle VM primary, Railway fallback)

## What it does

Allows Hermes to be deployed to either an Oracle VM (via Coolify) or Railway. Oracle VM is the primary target. Railway is kept as a fallback.

## Motivation

Oracle VM is free (already provisioned) and has more compute than Railway's hobby tier. Coolify provides a Railway-like experience — git-triggered deploys, env var management, SSL — but self-hosted. No vendor lock-in.

## Acceptance criteria

- [ ] `infra/coolify-setup.sh` provisions a new Hermes instance in Coolify with a single command (after one-time GitHub source setup)
- [ ] `infra/docker-compose.yml` allows running Hermes locally or on any Docker host without Coolify
- [ ] `railway.toml` remains valid and Railway deploys continue to work
- [ ] Claude Code can restart/debug Hermes on Oracle VM using WebFetch against the Coolify REST API
- [ ] No secrets in repo; env vars sourced from `infra/.env.coolify` (gitignored) or Coolify UI

## Deployment targets

| Target | Config | Deploy trigger | Debug from Claude Code |
|---|---|---|---|
| Oracle VM (primary) | `infra/coolify-setup.sh` | Coolify webhook on git push to `main` | `WebFetch $COOLIFY_URL/api/v1/applications/$HERMES_APP_UUID/...` |
| Railway (fallback) | `railway.toml` | Railway git push | Railway MCP tools in `.mcp.json` |

## Coolify REST API — debugging reference

Claude Code uses `WebFetch` with these endpoints (no MCP server needed):

```
Base: $COOLIFY_URL/api/v1
Auth: Authorization: Bearer $COOLIFY_TOKEN

GET  /applications/$HERMES_APP_UUID          — service status
GET  /applications/$HERMES_APP_UUID/logs     — container logs
POST /applications/$HERMES_APP_UUID/restart  — restart
POST /applications/$HERMES_APP_UUID/deploy   — redeploy
GET  /deployments?application_uuid=...       — deployment history
```

Required env vars for Claude Code sessions:
- `COOLIFY_URL` — e.g. `http://1.2.3.4:8000`
- `COOLIFY_TOKEN` — API token from Coolify UI
- `HERMES_APP_UUID` — printed by `coolify-setup.sh` on first run

## Open questions

- Coolify auto-SSL via Let's Encrypt requires a domain with DNS pointing to Oracle VM — optional but recommended for Telegram/Slack webhooks.
- Oracle Cloud free tier VMs have periodic maintenance reboots — Coolify's `restart: on-failure` handles this.

## Files

- `infra/coolify-setup.sh` — provisioning script
- `infra/.env.coolify.example` — env var template (copy to `.env.coolify`)
- `infra/docker-compose.yml` — manual Docker fallback
- `railway.toml` — Railway config (unchanged)
