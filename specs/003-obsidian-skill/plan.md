# 003 — Plan: Obsidian Vault Skill

## Overview

Two files to create: `skills/obsidian-vault/SKILL.md` and `skills/obsidian-vault/vault.py`.
The Dockerfile will need to copy `skills/` into the image so the agent can find them.

## Constitution Check

- No secrets committed (HERMES_VAULT_GIT_TOKEN is injected at runtime via Railway env vars)
- Write allowlist prevents the agent from modifying arbitrary vault paths
- All git operations shell out to subprocess — no gitpython dependency

## Dockerfile Change Required

The `skills/` directory in this repo needs to be copied into the Docker image at build
time so it lands in `/data/.hermes/skills/` on container start. Add to Dockerfile:

```dockerfile
COPY skills/ /data/.hermes/skills/
```

Place this after the `COPY server.py` line.

## vault.py Design

- Pure stdlib — no third-party dependencies beyond what's in the image (git is installed)
- Under 200 lines
- One function per tool, invoked via `argparse` subcommands
- Pulls before reads (5-min cache via `.last-pull` timestamp in vault root)
- `fcntl.flock` on `/data/.hermes/vault/.hermes.lock` for concurrent-write safety
- Missing token → `sys.exit(1)` with a clear message printed to stderr
- Merge conflict → print error to stdout (agent sees it), exit non-zero

## SKILL.md Design

Frontmatter declares `name`, `description`, `required_environment_variables`.
Body explains to the agent:
- Where vault.py lives: `/data/.hermes/skills/obsidian-vault/vault.py`
- How to call each subcommand
- What the output format is (JSON for list, plain text for read, status for write)
- What the write allowlist means and how to explain rejections to the user

## Step-by-Step

1. Create `skills/obsidian-vault/vault.py` (CLI with 5 subcommands)
2. Create `skills/obsidian-vault/SKILL.md` (agent instructions)
3. Edit `Dockerfile` — add `COPY skills/ /data/.hermes/skills/`
4. Verify with: `docker build -t hermes-agent . && docker run --rm -e HERMES_VAULT_GIT_TOKEN=... hermes-agent python /data/.hermes/skills/obsidian-vault/vault.py list agent-inbox`

## Risks / Notes

- Skills are auto-discovered at `/data/.hermes/skills/` — no config.yaml entry needed
- If the vault hasn't been cloned yet, `vault.py` handles first-clone automatically
- The `.last-pull` file is per-container (not persisted to the volume unless vault is mounted there, which it is since clone target is inside `/data/.hermes/`)
