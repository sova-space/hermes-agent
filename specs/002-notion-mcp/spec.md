# 002 — Notion MCP Integration

## Status
Config/documentation only — no code changes.

## What This Is

This spec documents how to connect the Hermes Agent to Notion via Notion's official
MCP (Model Context Protocol) server. Once connected, the agent can read and write Notion
pages it has been granted access to.

## MCP Server Details

- **Provider**: Notion (official)
- **Transport**: HTTP (remote, cloud-hosted by Notion)
- **URL**: `https://mcp.notion.com/mcp`
- **Auth**: OAuth 2.0 (handled in the Hermes dashboard)

## config.yaml Snippet

Add the following to the `mcpServers` section of `/data/.hermes/config.yaml`.
The Hermes dashboard will do this for you if you use the MCP Servers UI, but for
reference the manual snippet is:

```yaml
mcpServers:
  notion:
    url: https://mcp.notion.com/mcp
    transport: http
```

No `Authorization` header is set manually — Hermes manages the OAuth token after
the user completes the authentication flow.

## OAuth Flow

1. Open the Hermes admin dashboard at your Railway URL.
2. Navigate to **MCP Servers** in the sidebar.
3. Find **Notion** and click **Authenticate**.
4. A Notion OAuth consent screen opens — log in and approve.
5. Notion redirects back to Hermes with a token; Hermes stores it in the volume.
6. The MCP server now appears as connected.

## Notion Page Scope

Grant the Notion integration access to the minimum set of pages needed:

- Only share pages the agent needs to read or write.
- Do not share the entire workspace — use Notion's page-level sharing to be precise.
- Recommended starting set: an "Agent Inbox" page and any task/project databases
  you want the agent to interact with.

To share a page: open the page in Notion → **Share** → select the Hermes integration
from your workspace connections.

## Verification Steps

- [ ] `config.yaml` contains the `notion` MCP server block
- [ ] Hermes dashboard shows Notion as **Connected**
- [ ] Ask the agent: "List my Notion pages" — it should enumerate shared pages
- [ ] Ask the agent to create a test page — confirm it appears in Notion
- [ ] Revoke access to a page in Notion — confirm agent can no longer see it

## Persistence

The OAuth token is stored in the Hermes volume at `/data/.hermes/`. It survives
container restarts. A Railway redeploy does **not** invalidate the token (unlike
session cookies, which are HMAC-signed with an ephemeral key).

Re-authentication is only needed if:
- The token is manually revoked in Notion's settings
- The Hermes volume is wiped
