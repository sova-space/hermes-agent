# 004 — Tasks: GitHub MCP + Self-Update Loop

## Completed

- [x] Write spec.md — document GitHub MCP config, SOUL.md purpose, env vars, verification
- [x] Write plan.md — step-by-step setup, risk notes
- [x] Write tasks.md (this file)
- [x] Create `skills/SOUL.md` — agent identity and PR-branch constraint

## Manual (user action required)

- [ ] Confirm `HERMES_GITHUB_PAT` is set in Railway env vars
- [ ] Add GitHub MCP config block to `/data/.hermes/config.yaml` via Hermes dashboard
- [ ] Restart gateway or redeploy to pick up config change
- [ ] Verify GitHub MCP shows as Connected in dashboard
- [ ] Run verification tests from spec.md (list PRs, create test branch/PR)
- [ ] Rotate `HERMES_GITHUB_PAT` to a purpose-scoped token (see morning-summary.md)
