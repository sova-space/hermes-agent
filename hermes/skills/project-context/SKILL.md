---
name: project-context
description: Track the active project context and switch with /project command
metadata:
  hermes:
    tags: [project, context, workflow]
    category: productivity
---

# Project Context

Tracks which project is currently active. Use this to tag output and stay oriented
across sessions.

## State

Active project is stored at `/data/.hermes/current_project.txt`.

At the start of each session, load it:

```bash
python /data/.hermes/skills/project-context/project.py get
```

Tag task updates, cron results, and autonomous output with `[<project>]` when the
context is relevant (e.g., `[hermes-finance] Sync completed`).

## Commands

`/project` is intercepted by the `agent-silence` plugin before reaching Hermes.

- `/project` — sends a keyboard with [Finance] [Wishlist] [Hermes] buttons. Tapping sets the active doer project.
- `/do <task>` — runs the task against the active project via Doer.
- `/do_<project> <task>` — runs on an explicit project and updates the stored selection.

Project state is held in-memory in the plugin (resets on redeploy). No file I/O needed.

## Known projects

- `hermes-agent` — this agent's own repo (sova-claw/hermes-agent)
- `hermes-finance` — Monobank finance API + bot (sova-claw/hermes-finance)
- `coxit` — work contract at COXIT
- `personal` — personal tasks with no specific repo
