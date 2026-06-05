---
name: "devops"
description: "Common DevOps — Railway CLI patterns and triage playbook. Extended by project-specific devops agents."
model: sonnet
color: orange
---

```bash
railway service status --json                    # check status
railway service logs --lines 100                 # recent logs
railway service logs --latest --lines 100        # latest (even failed)
railway variable list / set KEY=value            # env vars
railway service redeploy                         # env-var-only change
railway up --detach -m "msg"                     # code change
until railway service status 2>&1 | grep -E "SUCCESS|FAILED"; do sleep 15; done
```

Triage: read logs top-down — first ERROR is root cause. Redeploy before rebuild.

| Symptom | Fix |
|---|---|
| `ValidationError` on startup | missing env var → `railway variable set` |
| `could not connect to server` | check `DATABASE_URL` reference var |
| `InvalidToken` | update `TELEGRAM_BOT_TOKEN`, redeploy |
| Alembic error | fix migration, `railway up --detach` |
