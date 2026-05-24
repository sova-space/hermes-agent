# 004 — Plan: GitHub MCP + Self-Update Loop

## Overview

Two deliverables:
1. Documentation of the GitHub MCP config snippet (user applies it via dashboard)
2. `skills/SOUL.md` — committed to the repo, bundled into the image, auto-discovered by Hermes

## Constitution Check

- No secrets committed — `HERMES_GITHUB_PAT` is injected at runtime
- SOUL.md explicitly constrains the agent from pushing to main, reducing blast radius
  of any agentic mistake

## Step-by-Step

### Step 1: Apply GitHub MCP Config

The user adds this to `/data/.hermes/config.yaml` via the Hermes dashboard or
directly via the admin API:

```yaml
mcpServers:
  github:
    url: https://api.githubcopilot.com/mcp/
    transport: http
    headers:
      Authorization: "Bearer ${HERMES_GITHUB_PAT}"
```

`HERMES_GITHUB_PAT` must already be set in Railway env vars and present in
`/data/.hermes/.env` (which `server.py` writes on startup from Railway env).

### Step 2: SOUL.md

Create `skills/SOUL.md` in the repo. It is bundled into the Docker image via the
existing `COPY skills/ /data/.hermes/skills/` Dockerfile directive (added in 003).

SOUL.md is a top-level identity file — not scoped to a subdirectory — placed
directly in `skills/` so it's discovered as `skills/SOUL.md` → `/data/.hermes/skills/SOUL.md`.

### Step 3: Verify

Follow verification steps in spec.md. Key check: ask the agent to propose a code
change and observe it creates `hermes-proposal/<slug>` branch + PR rather than
pushing to main.

## Risk Notes

- If `HERMES_GITHUB_PAT` is not set, the GitHub MCP connection will return 401.
  The agent will report it as unavailable. Set the token in Railway vars and restart.
- SOUL.md is a soft constraint — it instructs the agent via prose. The token's
  actual repo permissions are the hard enforcement layer.
- The PAT should have the minimum scopes needed. Do not use a broad `hermes-all`
  token long-term — see morning-summary.md for token rotation instructions.
