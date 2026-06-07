# agent-silence

Hermes gateway plugin. Two jobs:

1. **Silence** other agents' `@`-addressed slash commands in multi-bot group
   chats (e.g. `/balance@sova_finance_bot` shouldn't get an "unknown command"
   reply from Hermes).
2. **Host** the `/project` Doer command surface — `/project <name>` makes a
   chat "active" for that project, after which every plain message in the
   chat (no `/`) is dispatched to it as a task. No separate `/do`: switching
   *is* selecting, and running a task *is* just talking. See
   "The /project command" below for the full flow and why every reply
   restates the active project's name.

## Module map

| Module               | Owns                                                          |
|----------------------|---------------------------------------------------------------|
| `chat_context.py`    | Typed extraction of chat/topic ids from a `MessageEvent`     |
| `telegram_client.py` | Raw Telegram Bot API access (`sendMessage`, `setMyCommands`) |
| `doer.py`            | Agent discovery (`AGENT_*_URL`), project list, per-chat session state |
| `commands.py`        | `/project` handler + the registry pattern for adding more   |
| `config.py`          | Env-var-derived config (`Config` dataclass)                  |
| `__init__.py`        | Thin glue: wires the gateway hook + command registration     |

## The /project command

`/project` merges what used to be two commands (`/project` to pick, `/do` to
run) into one, on the idea that *picking a project IS entering a mode where
this chat talks to that project*:

| Typed                 | Effect                                                          |
|-----------------------|-----------------------------------------------------------------|
| `/project`            | Report the chat's active project (if any) + the available list |
| `/project <name>`     | Make `<name>` the chat's active project                        |
| *(any plain message)* | If the chat has an active project, dispatch the message to it as a task — otherwise fall through to normal agent chat |

So the flow is: `/project hermes` → "Project set to *hermes*. Send a plain
message to run it as a task on `hermes`" → "fix the header bug" → "Got it —
Doer is working on `hermes`. Result in #projects." Switching projects is just
`/project wishlist` again — no extra command to remember.

**Every reply that touches the active project restates its name** (`handle_project`
/ `handle_active_project_task` in `commands.py`). Once a chat is "in" a
project, plain messages stop being plain chat — that's a real mode switch a
busy group chat can easily lose track of, so the bot never lets a project
name go unstated when it matters.

## The bug this package was rewritten to prevent

`MessageEvent` (Hermes's normalized event) does **not** look like a raw
`python-telegram-bot` `Update`. It has no `chat_id`, `chat`, or `message`
attribute. The chat/topic identifiers live one level down, on
`event.source` (a `SessionSource`):

```python
event.source.chat_id    # str — yes, a string, even though it's Telegram's numeric id
event.source.thread_id  # str | None — forum topic id, also a string
```

The original version of this plugin read `event.chat_id` /
`event.chat.id` / `event.message.chat["id"]` — none of which exist.
Every one of those `getattr(..., None)` chains silently returned `None`,
so `chat_id` was always `None`, and the message-send helper's
`if not chat_id: return` guard ate every reply. The result: `/project`
showed up in Telegram's menu and did *visibly nothing* when invoked — no
error, no reply, nothing in the logs (the gateway catches and swallows hook
exceptions, and this wasn't even an exception — just silently wrong data).

**Always go through `ChatContext.from_event(event)`.** That's the one place
that knows where these ids actually live, and it's where the next platform
quirk (Discord threads, forum "General" topic id `"1"` rejecting
`message_thread_id`, …) should be handled — not re-discovered ad hoc in a
handler.

## Adding a new command

See the docstring at the top of `commands.py` — the short version:

1. Write `def handle_foo(ctx: CommandContext) -> dict | None`. Reply with
   `ctx.telegram.send_message(ctx.chat, ...)`. Return `skip("why")` to stop
   the gateway from falling through to normal agent dispatch, or `None` to
   let it.
2. Add it to `COMMANDS` in `commands.py` — exact-name match against the
   parsed command. (`route()` is the place to extend if a future command
   needs prefix-family matching, e.g. `/foo_<arg>`; none currently does.)
3. If it should appear in the `/` menu **inside group chats**, add a
   `BotCommand` to `GROUP_VISIBLE_COMMANDS` in `__init__.py`. This is a
   *separate* registration from `ctx.register_command` — Telegram does not
   surface default-scope commands in group chats, only commands explicitly
   pushed to the `all_group_chats` (or per-chat) scope. Skipping this step
   means the command works when typed but never appears in the menu.

`CommandContext` exists specifically so handlers never reach into the raw
`MessageEvent` — every dependency a handler needs (chat, parsed args, the
Telegram client, the Doer gateway, session state) is bundled there.

## Why raw `httpx` + dicts for Telegram, not `python-telegram-bot`

Plugins run inside the shared Hermes gateway process, which only depends on
`httpx`/stdlib. `python-telegram-bot` (with its typed `BotCommand`,
`BotCommandScopeAllGroupChats`, etc. — see `bots/finance/finance_api/domains/bot/commands.py`)
is a per-bot-service dependency declared by each bot's own `pyproject.toml`,
not something plugin code can import. `TelegramClient` is the one place that
owns the raw-HTTP shape so future Telegram calls don't each reinvent the
URL template / token guard / error-swallowing contract.
