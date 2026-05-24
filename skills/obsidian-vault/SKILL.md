---
name: obsidian-vault
description: Read and write notes in the Obsidian vault stored in the sova-claw/hermes-vault GitHub repo
required_environment_variables:
  - HERMES_VAULT_GIT_TOKEN
metadata:
  hermes:
    tags: [obsidian, notes, vault, github]
    category: productivity
---

# Obsidian Vault

This skill gives you access to a private Obsidian note vault stored in the
`sova-claw/hermes-vault` GitHub repository. The vault is cloned locally to
`/data/.hermes/vault/` on first use and kept up to date with a 5-minute pull
cache.

## CLI

All vault operations go through:

```
python /data/.hermes/skills/obsidian-vault/vault.py <subcommand> [args]
```

## Subcommands

### List notes in a folder

```bash
python /data/.hermes/skills/obsidian-vault/vault.py list <folder>
```

Output: JSON array of paths relative to the vault root, e.g. `["agent-inbox/task-1.md"]`.
Use `agent-inbox` as the default folder unless the user specifies another.

### Read a note

```bash
python /data/.hermes/skills/obsidian-vault/vault.py read <path>
```

Output: the full text of the note. Path is relative to the vault root.

### Write a note (overwrite)

```bash
python /data/.hermes/skills/obsidian-vault/vault.py write <path> "<content>"
```

Overwrites the note at `<path>`. The commit message will be `chore(hermes): write <path>`.
Only paths inside `agent-inbox/` or `daily/` are allowed by default. If the user asks
to write elsewhere, explain the allowlist and ask them to set `HERMES_VAULT_ALLOW_DIRS`.

### Append to a note

```bash
python /data/.hermes/skills/obsidian-vault/vault.py append <path> "<content>"
```

Appends content to an existing note (or creates it). Commit message: `chore(hermes): append <path>`.
Same allowlist applies.

### Search notes

```bash
python /data/.hermes/skills/obsidian-vault/vault.py search "<query>"
```

Output: JSON array of paths containing the search text.

## Behavior Notes

- **First use**: the script clones the vault automatically. No manual setup needed.
- **Merge conflicts**: if a pull results in a conflict, the script exits with an error
  message. Tell the user to resolve the conflict manually in the vault repo.
- **Write rejections**: if a path is outside the allowed directories, the script prints
  a clear error. Show the user the error and suggest they update `HERMES_VAULT_ALLOW_DIRS`.
- **Concurrent writes**: the script uses a file lock to prevent corruption when the
  agent runs multiple write operations close together.

## Daily Notes Convention

Daily notes live in `daily/YYYY-MM-DD.md`. When logging a daily summary, use today's
date as the filename and append to it rather than overwriting.

## Agent Inbox Convention

The `agent-inbox/` folder is for tasks left by the user for the agent. List this
folder at the start of each session and process any items found there.
