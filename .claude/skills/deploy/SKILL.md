---
name: deploy
description: Deploy Hermes services to Railway. Link commands, deploy commands, and health verification.
model: sonnet
version: 1.4.0
---

Topology and service IDs: see CLAUDE.md. Auto-deploy active on `main` push per watch pattern; `entrypoint.sh` runs `alembic upgrade head` — migration errors crash before health check.

## Deploy

**Code changes** → `git push origin main` — all services auto-deploy on main push. Never use `railway up`.

**Env-var-only change** → use Railway MCP plugin:
```
mcp__plugin_railway_railway__set_variables(project_id, environment_id, service_id, variables={...})
```
This triggers a redeploy automatically.

## Check status

```
mcp__plugin_railway_railway__environment_status(
  project_id="3d73dc58-1201-4258-bc1d-1f9c24333032",
  environment_id="a2a88403-f2b1-4a18-a44d-3b808d07bcb1"
)
```

## Health URLs

```
Hermes Agent:  hermes-agent-production-d21c.up.railway.app/health
Finance:       hermes-finance-production.up.railway.app/health
```
