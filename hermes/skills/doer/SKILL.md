---
name: doer
description: Delegate development tasks to the Doer agent — creates PRs and merges them autonomously.
metadata:
  hermes:
    tags: [doer, dev, code, pr, github, do]
    category: development
---

# Doer

Doer is an autonomous developer agent. It reads the relevant code, makes changes, opens a PR, and merges it. Results appear in `#projects`.

Base URL: `${AGENT_DOER_URL}`

---

## Routing — read this first

The `agent-silence` plugin intercepts all doer commands before they reach Hermes. You only see doer-related messages if the plugin is not loaded.

**Triggers:**
- `/project` — shows a project picker keyboard (Finance / Wishlist / Hermes)
- `/do <task>` — runs task on the currently selected project
- `/do_<project> <task>` — runs task on an explicit project (also updates the stored project)

Do NOT handle conversational questions about code. Only trigger on explicit doer commands.

---

## Dispatch

Call `POST ${AGENT_DOER_URL}/task` with:

```json
{
  "project": "<project>",
  "task": "<task description>"
}
```

The endpoint returns immediately with a `task_id`. Respond to the user:

> Got it — Doer is working on `<project>`. I'll post the result in #projects.

Do not wait for the task to finish. Results arrive in #projects automatically.

---

## Projects

| Project | Repo |
|---|---|
| `finance` | sova-claw/hermes-finance |
| `wishlist` | sova-claw/hermes-wishlist |
| `hermes` | nkhimin/hermes-agent |

---

## Error handling

If `POST /task` returns 400 (unknown project), tell the user the project name is not recognised and list the known ones.
If the request fails entirely, say "Doer is unavailable right now".
