# 003 — Tasks: Obsidian Vault Skill

## Completed

- [x] Write spec.md — document skill format, vault.py design, env vars, verification
- [x] Write plan.md — Dockerfile change, vault.py and SKILL.md design details
- [x] Write tasks.md (this file)
- [x] Create `skills/obsidian-vault/vault.py` — git-backed vault CLI
- [x] Create `skills/obsidian-vault/SKILL.md` — Hermes agent instructions
- [x] Edit `Dockerfile` — add `COPY skills/ /data/.hermes/skills/`

## Manual (user action required)

- [ ] Set `HERMES_VAULT_GIT_TOKEN` in Railway env vars (fine-grained PAT for sova-claw/hermes-vault)
- [ ] Optionally set `HERMES_VAULT_ALLOW_DIRS` if you want to allow writes beyond agent-inbox and daily
- [ ] Redeploy Railway service to pick up the new image
- [ ] Test: ask agent "list notes in agent-inbox/"
- [ ] Test: ask agent to write a note and verify the commit appears in hermes-vault repo
