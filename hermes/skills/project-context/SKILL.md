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
context is relevant (e.g., `[finance] Sync completed`).

## Commands

`/project` is intercepted by the `agent-silence` plugin before reaching Hermes.

- `/project` — sends a keyboard with [Finance] [Wishlist] [Hermes] buttons. Tapping sets the active doer project.
- `/do <task>` — runs the task against the active project via Doer.
- `/do_<project> <task>` — runs on an explicit project and updates the stored selection.

Project state is held in-memory in the plugin (resets on redeploy). No file I/O needed.

## Known projects

Mirrors the Doer project registry (`bots/doer/doer_api/agent/projects.py`) so the
labels here always match what `/project <name>` switches to:

- `finance` — Monobank finance API + bot (sova-claw/hermes-finance)
- `wishlist` — wishlist bot (sova-claw/hermes-wishlist)
- `hermes` — this agent's own repo (nkhimin/hermes-agent)
