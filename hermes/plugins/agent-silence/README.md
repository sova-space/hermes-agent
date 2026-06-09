# agent-silence

Hermes gateway plugin. Two jobs:

1. **Silence** other agents' `@`-addressed slash commands in multi-bot group chats (e.g. `/balance@sova_finance_bot` shouldn't get an "unknown command" from Hermes).
2. **Host** the `/profile` + `/mode` routing surface — profile picks a project, mode decides how plain messages route.

## How routing works

```
/profile finance          → activates "finance" profile for this chat
/mode client              → plain messages → finance bot's domain assistant (Q&A)
/mode dev                 → plain messages → GitHub agent loop on sova-claw/hermes-finance
```

Mode is sticky per chat. Default is `client` — the safe no-op that can't accidentally trigger code changes.

## Module map

| Module | Owns |
|---|---|
| `chat_context.py` | Typed extraction of chat/topic ids from `MessageEvent` |
| `telegram_client.py` | Raw Telegram Bot API (`sendMessage`, `setMyCommands`) |
| `doer.py` | Agent discovery (`AGENT_*_URL`), profile list, per-chat session state (profile + mode) |
| `devops.py` | In-process GitHub agent loop — reads/writes code, opens PRs, posts to #projects |
| `commands.py` | `/profile`, `/mode` handlers + the pattern for adding more |
| `config.py` | Env-var config (`TELEGRAM_BOT_TOKEN`, `GITHUB_TOKEN`, `OPENROUTER_API_KEY`, `DEVOPS_MODEL`) |
| `__init__.py` | Thin glue: gateway hook + command registration |

## Adding a command

1. Write `def handle_foo(ctx: CommandContext) -> dict | None`. Reply via `ctx.telegram.send_message(ctx.chat, ...)`. Return `skip("reason")` to stop gateway fallthrough, `None` to allow it.
2. Add to `COMMANDS` in `commands.py`.
3. If it should appear in the `/` group menu: add a `BotCommand` to `GROUP_VISIBLE_COMMANDS` in `__init__.py` (group chats don't surface default-scope commands — skipping this makes it invisible in the menu even though it works when typed).

## The chat_id bug — don't repeat it

`MessageEvent` does **not** have `.chat_id`, `.chat`, or `.message`. The ids live on `event.source`:

```python
event.source.chat_id    # str — always a string, even though it's Telegram's numeric id
event.source.thread_id  # str | None — forum topic id
```

**Always use `ChatContext.from_event(event)`** — never read `event.source` directly in a handler.

## Why raw httpx for Telegram

Plugins run inside the shared Hermes gateway process, which only has `httpx`/stdlib. `python-telegram-bot` is a per-bot dependency — plugin code can't import it. `TelegramClient` owns the raw-HTTP shape so future calls don't each reinvent the URL template.
