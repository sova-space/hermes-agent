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

### Show current project

When the user sends `/project` with no arguments:

```bash
python /data/.hermes/skills/project-context/project.py get
```

Reply: `Active project: <name>`

### Switch project

When the user sends `/project <name>`:

```bash
python /data/.hermes/skills/project-context/project.py set <name>
```

Reply: `Switched to <name>`

### List projects

When the user sends `/project list`:

```bash
python /data/.hermes/skills/project-context/project.py list
```

Reply with the returned list, marking the active one with `*`.

## Known projects

- `hermes-agent` — this agent's own repo (sova-claw/hermes-agent)
- `hermes-finance` — Monobank finance API + bot (sova-claw/hermes-finance)
- `coxit` — work contract at COXIT
- `personal` — personal tasks with no specific repo
