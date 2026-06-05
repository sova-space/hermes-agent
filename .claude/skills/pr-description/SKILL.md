---
name: pr-description
description: Generate a concise PR description from the current branch diff. Outputs a filled-in template ready to paste into GitHub.
version: 1.1.0
---

1. `git log main...HEAD --oneline` — see all commits
2. `git diff main...HEAD --stat` — files changed
3. `git diff main...HEAD` — full diff
4. Fill template below. Use `gh auth switch --user sova-claw` before creating the PR.

**Rules:** 2–4 bullets max. Describe behaviour, not implementation. Imperative verbs (Add, Fix, Expose, Remove). No file names, function names, or commit hashes. No "this PR" / "this change" / "I".

```
### What does it do?

- <bullet>

### What else do you need to know?

<non-obvious constraint, migration step, or breaking change — leave blank otherwise>

### Checklist
- [ ] Base branch is `main`
- [ ] Adds or updates tests
- [ ] Tested manually
- [ ] Ruff clean (`uv run ruff check .`)
- [ ] New env vars added to Railway (if any)
- [ ] Alembic migration included if schema changed

### Demo screenshots or video, if any
```
