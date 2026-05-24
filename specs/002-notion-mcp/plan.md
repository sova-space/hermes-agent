# 002 — Plan: Notion MCP Integration

## Overview

No code is written for this feature. The plan covers the steps to configure and
verify the Notion MCP connection on the running Railway deployment.

## Constitution Check

Documentation only. No credentials committed. Complies with Principles I, IV, VII.

## Step-by-Step Setup

### Step 1: Verify config.yaml is reachable

SSH into the Railway shell (or check via the admin logs) and confirm:

```bash
cat /data/.hermes/config.yaml
```

The file should exist. If `mcpServers` is not present, the Hermes dashboard will
add it when you authenticate.

### Step 2: Authenticate via Dashboard

Follow the OAuth flow described in `spec.md`. After completion, verify the token
is saved:

```bash
ls /data/.hermes/
# Should include a notion-related token or credential file
```

### Step 3: Share Notion Pages

In Notion:
1. Open each page you want the agent to access.
2. Click **Share** → search for the Hermes integration connection.
3. Confirm the connection appears.

Recommended page set to share initially:
- `Agent Inbox` (agent drops incoming tasks here)
- `Daily Notes` (if you want the agent to log daily summaries)
- Any project database the agent should update

Do **not** share the full workspace — keep scope narrow.

### Step 4: Verify End-to-End

Run these test prompts in the Hermes dashboard or Telegram bot:

1. "List all Notion pages you can access" — should return the shared pages only
2. "Read the Agent Inbox page" — should return its content
3. "Append a test line to Agent Inbox" — should update the page in Notion

### Step 5: Confirm Persistence

Trigger a Railway redeploy (or restart the gateway from the dashboard) and repeat
Step 4. The MCP connection should still be active without re-authenticating.

## config.yaml Reference

```yaml
mcpServers:
  notion:
    url: https://mcp.notion.com/mcp
    transport: http
```

## Risks / Notes

- If Notion changes its MCP URL, update `config.yaml` and re-authenticate.
- The OAuth token is user-specific — each Hermes instance (each Railway deploy)
  needs its own authentication.
- If you wipe the `/data` volume, the token is lost and you must re-authenticate.
