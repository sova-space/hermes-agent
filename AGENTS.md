# AGENTS.md

Rules for AI agents working in this repo. Human docs → `README.md`.

## What this is

**Hermes** — Nazar's personal AI agent on Railway. Connects Telegram + Slack, reads/writes Notion + Obsidian, self-updates via GitHub PRs.

Runtime: **Hermes Agent** by Nous Research. Config only — no fork.

## Layout

```
hermes-agent/
├── AGENTS.md
├── CLAUDE.md
├── railway.toml
├── server.py
├── pyproject.toml
├── hermes/
│   ├── config/          ← SOUL.md, STYLE.md, channels.md, telegram.yaml, slack.yaml
│   └── skills/          ← obsidian-vault/
├── infra/               ← Dockerfile, start.sh, templates/
├── specs/               ← NNN-feature-slug/{spec,plan,tasks}.md
└── docs/                ← constitution.md
```

Obsidian vault: separate repo `sova-claw/hermes-vault`.

## Hard rules

1. **Specs first** — no code without `specs/NNN-feature/spec.md`
2. **PR only** — branch → PR → merge. No direct pushes to `main`
3. **No secrets** — all tokens in Railway env vars only
4. **Token separation** — `HERMES_GITHUB_PAT` for agent repo, `HERMES_VAULT_GIT_TOKEN` for vault repo. Never overlap.
5. **MCP first** — use official MCP servers before writing custom skills
6. **One Railway service** — no second always-on service without Nazar's approval
7. **Verify** — docs > assumptions. Check hermes-agent.nousresearch.com/docs

## Workflow

- Config tweaks, single-file → Hermes does remotely
- Multi-file, complex logic → Nazar codes locally → push → PR → Hermes reviews → merge
- Architecture decisions → discuss first

## Commits

Conventional Commits: `type(scope): description`
Types: `feat`, `fix`, `chore`, `docs`, `refactor`

## Output style

See `hermes/config/STYLE.md`. Key: no fluff, fragments OK, bullets for lists, result-only tool output.

## Out of scope

Multi-user, public endpoints, forking Hermes runtime, financial transactions.
