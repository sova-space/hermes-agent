---
name: deploy
description: Deploy Hermes services to Railway. Link commands, deploy commands, and health verification.
model: sonnet
version: 1.4.0
---

Topology and service IDs: see CLAUDE.md. Auto-deploy active on `main` push; `entrypoint.sh` runs `alembic upgrade head` — migration errors crash before health check.

## Link + deploy

```bash
# Hermes Agent (from repo root)
railway link --project 3d73dc58 --service 8d1fc2f6 --environment a2a88403
railway up --detach -m "msg"

# Finance (from bots/finance/)
railway link --project 3d73dc58 --service 9bc27c48 --environment a2a88403
railway up --detach -m "msg"

# Wishlist (from bots/wishlist/)
railway link --project 3d73dc58 --service 7764e517 --environment a2a88403
railway up --detach -m "msg"
```

## Health URLs

```
Hermes Agent:  hermes-agent-production-d21c.up.railway.app/health
Finance:       hermes-finance-production.up.railway.app/health
```
