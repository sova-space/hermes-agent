# Morning Summary — 2026-05-25

## Done

- [#1 — 001: Railway bootstrap documentation](https://github.com/sova-claw/hermes-agent/pull/1) — Documents existing Railway setup, env vars, volume path, architecture, and a verification checklist
- [#2 — 002: Notion MCP integration](https://github.com/sova-claw/hermes-agent/pull/2) — Documents Notion MCP config, OAuth flow, page scope recommendations
- [#3 — 003: Obsidian vault skill](https://github.com/sova-claw/hermes-agent/pull/3) — Adds `vault.py` CLI and `skills/obsidian-vault/SKILL.md`; agent can now read/write your Obsidian vault via GitHub
- [#4 — 004: GitHub MCP + self-update loop](https://github.com/sova-claw/hermes-agent/pull/4) — Documents GitHub MCP config; adds `skills/SOUL.md` constraining agent to PR-only self-modifications

## You need to do (in order)

1. **Rotate the GitHub token** — `hermes-all` was exposed in chat during setup.
   Create a new fine-grained PAT at https://github.com/settings/personal-access-tokens/new
   (same permissions as before), then update Railway vars:
   - `HERMES_VAULT_GIT_TOKEN` — scoped to `sova-claw/hermes-vault` only (contents: read+write)
   - `HERMES_GITHUB_PAT` — scoped to `sova-claw/hermes-agent` only (contents: write, pull-requests: write, issues: write)
   
   After updating, revoke the old `hermes-all` token on GitHub.

2. **Authenticate Notion MCP** — open the Hermes dashboard → MCP Servers → Notion → authenticate via OAuth.
   Share only the pages you want the agent to access (narrow scope).

3. **Add GitHub MCP config** — in the Hermes dashboard config editor, add:
   ```yaml
   mcpServers:
     github:
       url: https://api.githubcopilot.com/mcp/
       transport: http
       headers:
         Authorization: "Bearer ${HERMES_GITHUB_PAT}"
   ```
   Then restart the gateway.

4. **Enable branch protection on main** — was skipped to allow autonomous merging tonight.
   Go to https://github.com/sova-claw/hermes-agent/settings/branches → add rule for `main`:
   require PR + 1 approval.

5. **Verify Telegram** — send a message to your bot and confirm it replies.

6. **Test Obsidian skill** — ask the agent: "list notes in agent-inbox/"

## Railway env vars still needed (if not already set in dashboard)

- `OPENROUTER_API_KEY` (or another provider key)
- `LLM_MODEL` (e.g. `openai/gpt-4o-mini`)
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_ALLOWED_USER_IDS`
- `ADMIN_PASSWORD`
- `HERMES_VAULT_GIT_TOKEN` (new, rotated token)
- `HERMES_GITHUB_PAT` (new, rotated token)
