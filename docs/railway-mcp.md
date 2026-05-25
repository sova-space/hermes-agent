# Railway MCP Reference

## Setup Checklist

1. **Get API token** — railway.com → project → Settings → Tokens → Create Token
2. **Add to env** — Railway dashboard → service → Variables → add `RAILWAY_API_TOKEN`
3. **Restart agent** — redeploy so Hermes picks up new MCP config + env var

## Config Location

`/data/.hermes/config.yaml` → `mcp_servers.railway`

```yaml
mcp_servers:
  railway:
    url: https://mcp.railway.app/sse
    headers:
      Authorization: "Bearer <token>"
    timeout: 60
    connect_timeout: 30
```

**IMPORTANT:** Token must be literal in YAML — no `$VAR` expansion. If token changes, update config AND redeploy.

## Key IDs (joyful-art project)

- Project: `3d73dc58-1201-4258-bc1d-1f9c24333032`
- Environment (production): `a2a88403-f2b1-4a18-a44d-3b80807bcb1`
- Service (Hermes Agent): `8d1fc2f6-031b-4527-9a7d-3e78316d1180`

## Available After Restart

MCP tools prefixed `mcp_railway_*` — call `mcp_railway_list_deployments`, `mcp_railway_redeploy`, etc.

## Pitfalls

- `$RAILWAY_API_TOKEN` in YAML does NOT expand — must write actual token
- `railway mcp` CLI subcommand only has `install` — no stdio server
- `railway whoami` needs `railway login` (browser auth) — can't do headlessly
- MCP HTTP endpoint: `https://mcp.railway.app/sse` (not `.com`)
- Config changes require agent restart (redeploy)
- GraphQL API token ≠ Railway environment token — different scopes
