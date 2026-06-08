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

`/profile` is intercepted by the `agent-silence` plugin before reaching Hermes
(`/project` still works as a back-compat alias — same handler, same state).
This is the profile router (see `specs/014-profile-router/spec.md`): once a
profile is active, two distinct things route two different ways —

- `/profile` — show the active profile + available choices.
- `/profile <name>` — switch (e.g. `/profile finance`).
- `/do <task>` — explicit devops verb: runs the task against the active
  profile's repo via Doer's generic GitHub loop. Result posted to #projects.
- a plain message (no leading `/`) — domain Q&A: routed to the active
  profile's own conversational assistant (e.g. `finance`'s money-question
  assistant), discovered via `GET /bot/profile` on its agent URL. Falls
  through to ordinary Hermes conversation if that profile has no registered
  assistant (e.g. `hermes` — there's no separate domain API to ask).

Profile state is held in-memory in the plugin (resets on redeploy). No file I/O needed.

## Known projects

Mirrors the Doer project registry (`bots/doer/doer_api/agent/projects.py`) so the
labels here always match what `/profile <name>` switches to:

- `finance` — Monobank finance API + bot (sova-claw/hermes-finance)
- `wishlist` — wishlist bot (sova-claw/hermes-wishlist)
- `hermes` — this agent's own repo (nkhimin/hermes-agent)
