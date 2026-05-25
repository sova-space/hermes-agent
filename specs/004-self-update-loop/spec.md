# 004 — GitHub MCP + Self-Update Loop

## Status
Config/documentation + one new skill file (`skills/SOUL.md`).

## What This Is

Two things in one feature:

1. **GitHub MCP**: connect the Hermes agent to GitHub via the official GitHub MCP
   server at `https://api.githubcopilot.com/mcp/`. This gives the agent tools to
   read/write issues, PRs, files, and branches in any repo the PAT has access to.

2. **SOUL.md**: an identity skill that constrains how the agent modifies the
   `sova-claw/hermes-agent` repo. All changes must go through a PR branch named
   `hermes-proposal/<slug>` — the agent never pushes to `main` directly.

## GitHub MCP Server Details

- **Provider**: GitHub (official Copilot MCP endpoint)
- **Transport**: HTTP remote
- **URL**: `https://api.githubcopilot.com/mcp/`
- **Auth**: Bearer token using `HERMES_GITHUB_PAT` env var

## config.yaml Snippet

```yaml
mcpServers:
  github:
    url: https://api.githubcopilot.com/mcp/
    transport: http
    headers:
      Authorization: "Bearer ${HERMES_GITHUB_PAT}"
```

The `${HERMES_GITHUB_PAT}` syntax is resolved by Hermes at runtime from the `.env`
file, which is deep-merged from Railway env vars on startup.

## SOUL.md — Agent Identity

`skills/SOUL.md` is a top-level skill file that acts as a standing instruction for
the agent. It tells the agent:

- Its identity and purpose in this deployment
- The rule that all changes to `sova-claw/hermes-agent` must use a PR branch named
  `hermes-proposal/<slug>`, never direct pushes to `main`
- Where to find the GitHub PAT (`HERMES_GITHUB_PAT` env var)
- Links to the specs/ directory as the source of truth for planned work

## Required Environment Variables

| Variable | Notes |
|---|---|
| `HERMES_GITHUB_PAT` | Fine-grained PAT with read+write access to `sova-claw/hermes-agent` |

The PAT needs at minimum: `contents: write`, `pull-requests: write`, `issues: write`
on the `sova-claw/hermes-agent` repository.

## Verification Steps

- [ ] `config.yaml` contains the `github` MCP server block
- [ ] Hermes dashboard shows GitHub MCP as **Connected**
- [ ] Ask agent "list open PRs on sova-claw/hermes-agent" — should return current PRs
- [ ] Ask agent to create a branch `hermes-proposal/test-001` and a draft PR — verify
  it appears on GitHub and follows the naming convention
- [ ] Confirm agent refuses to push directly to `main` (SOUL.md constraint)
