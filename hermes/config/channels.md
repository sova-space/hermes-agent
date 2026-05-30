# Hermes PI — Channel Routing

## Telegram (delegation + home delivery)

Supergroup: Hermes PI
Home channel: #projects topic

| Topic | Purpose | Direction |
|---|---|---|
| #general    | Quick asks, delegation, ad-hoc requests | You → Hermes |
| #projects   | Cron results, status updates, autonomous output | Hermes → you |
| #finance    | Balance checks, spending queries, sync triggers | Both |

## Slack (execution tracking)

Workspace: Hermes PI

| Channel | Purpose | Direction |
|---|---|---|
| #status   | Task lifecycle: started / done / failed / blocked | Hermes → you |
| #digest   | Scheduled reports, self-update PRs, errors | Hermes → you |

## Routing rules

- Hermes replies to delegation in the same topic it was asked from
- All proactive / scheduled output goes to Telegram #projects (home channel)
- Task lifecycle updates mirror to Slack #status
- Autonomous scheduled output also mirrors to Slack #digest
- Urgent clarifications (blocking a task): Hermes asks in Telegram #general
- Non-urgent clarifications: Hermes posts in Slack #status and waits

## Topic / Channel IDs

| ID | Value |
|---|---|
| Telegram supergroup | -1003913424869 |
| Telegram #general topic | 173 |
| Telegram #projects topic | 167 |
| Telegram #finance topic | 1192 |
| Slack #status channel | FILL_IN |
| Slack #digest channel | FILL_IN |
