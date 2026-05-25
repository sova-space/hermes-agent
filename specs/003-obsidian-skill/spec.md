# 003 — Obsidian Vault Skill

## Status
Code + config. Creates `skills/obsidian-vault/SKILL.md` and `skills/obsidian-vault/vault.py`.

## What This Is

A Hermes skill that lets the agent read and write notes in a private Obsidian vault
stored in the `sova-claw/hermes-vault` GitHub repository.

## Skill Format

Hermes skills are SKILL.md files with YAML frontmatter, auto-discovered from
`/data/.hermes/skills/<name>/SKILL.md`. No registration in config.yaml is required.
The SKILL.md body contains prose instructions — the agent reads them and executes
the procedure using its bash and file tools.

## Implementation Pattern

Because skills are declarative (no `script:` or executable frontmatter), the
SKILL.md instructs the agent to invoke `vault.py` as a CLI via bash. The vault.py
script handles git clone/pull, file I/O, and git commit/push.

```
/data/.hermes/skills/obsidian-vault/
├── SKILL.md     ← agent instructions, auto-discovered by Hermes
└── vault.py     ← CLI invoked by the agent via bash
```

## vault.py Capabilities

Subcommands:
- `list <folder>` — list markdown files in a vault folder (JSON array to stdout)
- `read <path>` — print note contents to stdout
- `write <path> <content>` — overwrite a note file
- `append <path> <content>` — append to a note file
- `search <query>` — grep for text across the vault, return matching file paths

## Git Vault Integration

- Repo: `https://github.com/sova-claw/hermes-vault.git`
- Clone target: `/data/.hermes/vault`
- Auth: uses `HERMES_VAULT_GIT_TOKEN` env var in the clone URL
- Pull strategy: pull before reads; skip if last pull was within 5 minutes
  (`.last-pull` timestamp file in vault root)
- Writes: after file change, runs `git add -A && git commit -m "chore(hermes): <action> <filename>" && git push`
- Merge conflict on pull: return error string, do not crash or lose data
- Concurrent writes: `fcntl.flock` on `/data/.hermes/vault/.hermes.lock`

## Write Allowlist

- Controlled by env var `HERMES_VAULT_ALLOW_DIRS` (comma-separated directory names)
- Default: `agent-inbox,daily`
- Writes to paths outside the allowlist are rejected with a clear error

## Required Environment Variables

| Variable | Notes |
|---|---|
| `HERMES_VAULT_GIT_TOKEN` | Fine-grained PAT with read+write access to `sova-claw/hermes-vault` |
| `HERMES_VAULT_ALLOW_DIRS` | Optional; defaults to `agent-inbox,daily` |

## Verification Steps

- [ ] `skills/obsidian-vault/` directory copied to `/data/.hermes/skills/obsidian-vault/` on deploy
- [ ] Agent responds to "list notes in agent-inbox/" by calling vault.py list
- [ ] Agent reads a note and returns its content
- [ ] Agent writes a note and the commit appears in the hermes-vault repo
- [ ] Write to an non-allowlisted folder is rejected
- [ ] After a container restart, the vault is re-pulled (not re-cloned)
