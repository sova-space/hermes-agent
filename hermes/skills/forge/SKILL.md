---
name: forge
description: Delegate development tasks to the Forge agent — creates PRs and merges them autonomously.
metadata:
  hermes:
    tags: [forge, dev, code, pr, github, do]
    category: development
---

# Forge

Forge is an autonomous developer agent. It reads the relevant code, makes changes, opens a PR, and merges it. Results appear in `#projects`.

Base URL: `${AGENT_FORGE_URL}`

---

## Routing — read this first

**Trigger**: any message starting with `/do_finance`, `/do_wishlist`, or `/do_hermes` (with or without bot suffix).

Extract:
- **project**: the part after `/do_` (e.g. `finance`)
- **task**: the rest of the message (everything after the command)

Do NOT handle conversational questions about code. Only trigger on explicit `/do_<project>` commands.

---

## Dispatch

Call `POST ${AGENT_FORGE_URL}/task` with:

```json
{
  "project": "<project>",
  "task": "<task description>"
}
```

The endpoint returns immediately with a `task_id`. Respond to the user:

> Got it — Forge is working on `<project>`. I'll post the result in #projects.

Do not wait for the task to finish. Results arrive in #projects automatically.

---

## Projects

| Command | Project |
|---|---|
| `/do_finance` | finance |
| `/do_wishlist` | wishlist |
| `/do_hermes` | hermes |

---

## Error handling

If `POST /task` returns 400 (unknown project), tell the user the project name is not recognised and list the known ones.
If the request fails entirely, say "Forge is unavailable right now".
