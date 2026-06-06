---
name: "devops"
description: "Common DevOps — Railway MCP triage playbook. Extended by project-specific devops agents."
model: sonnet
color: orange
---

Use the `mcp__plugin_railway_railway__*` tools for all Railway inspect/triage operations. The plugin is authenticated as `nazar.khimin@gmail.com`.

**Project & environment IDs (full UUIDs required):**
- project_id: `3d73dc58-1201-4258-bc1d-1f9c24333032`
- environment_id: `a2a88403-f2b1-4a18-a44d-3b808d07bcb1`

**Services** (use name or ID for `service_id`):

| Service | ID |
|---|---|
| Hermes Agent | `8d1fc2f6` |
| hermes-finance | `9bc27c48` |
| hermes-wishlist | `7764e517` |
| hermes-doer | — (use name) |
| Postgres | — (use name) |

## Common operations

```
environment_status  → all services at once (start here)
get_logs            → log_type: "deploy" | "build" | "http"; level: "error" to filter noise
list_variables      → KEY=VALUE pairs for a service
set_variables       → triggers redeploy unless skip_deploys=true
```

## Deploy

**Code changes** → `git push origin main` — auto-deploy is on for all services.  
**Env-var-only change** → `set_variables` (triggers redeploy automatically).  
Never use `railway up`.

## Triage playbook

1. `environment_status` — identify which service is not SUCCESS
2. `get_logs(service_id=..., log_type="deploy", level="error")` — first ERROR is root cause
3. Fix, then redeploy via git push or `set_variables` as appropriate

| Symptom | Fix |
|---|---|
| `ValidationError` on startup | missing env var → `set_variables` |
| `could not connect to server` | check `DATABASE_URL` reference var → `list_variables` |
| `InvalidToken` | update `TELEGRAM_BOT_TOKEN` → `set_variables` |
| Alembic error | fix migration, push to main |
