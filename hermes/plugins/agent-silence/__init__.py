"""Hermes plugin: silences other agents' @-addressed commands in group chats,
and hosts the /profile + /do profile-router command surface.

This module is intentionally thin — it wires the gateway hook/command
registration to the pieces that hold the actual logic:

- ``chat_context``    — typed extraction of chat/thread ids from MessageEvent
- ``telegram_client`` — raw Telegram Bot API access
- ``doer``            — agent discovery, profile registry, dispatch + ask
- ``commands``        — /profile, /do, message-routing + the pattern for more

See ``commands.py`` for "how do I add a new command", ``specs/014-profile-router/``
for the routing design, and ``README.md`` for the full architecture writeup
(in particular: why ``event.source``, not ``event``, is where chat/thread ids
live — that one cost a debugging session).
"""

from .chat_context import ChatContext
from .commands import (
    COMMAND_DO,
    COMMAND_PROFILE,
    COMMAND_PROJECT_ALIAS,
    CommandContext,
    handle_profile_message,
    route,
    skip,
)
from .config import CONFIG
from .doer import DoerGateway, DoerSession
from .telegram_client import BotCommand, TelegramClient

# Commands surfaced in Telegram's `/` menu *inside group chats*. This is a
# separate registration path from ctx.register_command below — group chats
# don't surface default-scope commands at all (see
# TelegramClient.register_group_commands / SCOPE_ALL_GROUP_CHATS for why).
GROUP_VISIBLE_COMMANDS = [
    BotCommand(COMMAND_PROFILE, "Show/switch the chat's active profile"),
    BotCommand(COMMAND_DO, "Run a devops task on the active profile's repo"),
]

_telegram = TelegramClient(CONFIG.TELEGRAM_BOT_TOKEN)
_doer = DoerGateway(CONFIG.DOER_URL)
_session = DoerSession()

# Chats whose per-chat command-scope override we've already cleared this
# process lifetime — see _clear_stale_chat_override. A plain set is enough:
# it's a one-shot-per-chat cleanup, not state that needs to survive restarts.
_cleared_chat_overrides: set[str] = set()


def _clear_stale_chat_override(chat_id: str | None) -> None:
    """Make sure ``chat_id`` has no leftover per-chat command override.

    Self-healing, once per chat per process: an old debugging probe once
    pushed a chat-scoped ``setMyCommands`` here (mirroring how the finance
    bot scopes ``/balance`` etc. to #finance) to test a hypothesis that
    didn't pan out — but the registration itself likely succeeded and stuck,
    silently shadowing every later ``all_group_chats`` update for that one
    chat (that's how a removed command like the old ``/do`` can keep showing
    up in the menu even after the group-wide list is correct). Clearing it
    is a single cheap, idempotent ``deleteMyCommands`` — see
    ``TelegramClient.clear_chat_command_overrides``.
    """
    if chat_id is None or chat_id in _cleared_chat_overrides:
        return
    _telegram.clear_chat_command_overrides(chat_id)
    _cleared_chat_overrides.add(chat_id)


def _command_args(text: str) -> str:
    """Everything after the command token, e.g. ``"/do fix bug"`` -> ``"fix bug"``."""
    parts = text.split(None, 1)
    return parts[1].strip() if len(parts) > 1 else ""


def _silence_if_owned_elsewhere(cmd: str, text: str) -> dict[str, str] | None:
    """Swallow @-addressed commands that belong to other registered agent
    bots, so Hermes doesn't reply "unknown command" on their behalf in
    multi-bot group chats like Sova Space.

    Only @-addressed invocations are silenced — a bare ``/balance`` (no
    ``@sova_finance_bot`` suffix) is ambiguous enough that staying silent
    could hide a genuine Hermes-side "unknown command", so we only act when
    the user explicitly disambiguated which bot they meant.
    """
    if cmd not in _doer.agent_commands:
        return None
    command_token = text.split()[0] if text else ""
    if "@" in command_token:
        return skip("agent bot command")
    return None


def pre_dispatch(event, **kwargs):
    _doer.load()

    text = getattr(event, "text", "") or ""
    cmd = event.get_command() if hasattr(event, "get_command") else None
    chat = ChatContext.from_event(event)
    _clear_stale_chat_override(chat.chat_id)
    ctx = CommandContext(
        chat=chat,
        text=text,
        args=_command_args(text),
        telegram=_telegram,
        doer=_doer,
        session=_session,
    )

    if cmd is None:
        return handle_profile_message(ctx)

    routed = route(cmd, ctx)
    if routed is not None:
        return routed

    return _silence_if_owned_elsewhere(cmd, text)


def _default_scope_profile(raw_args: str) -> str:
    """Fallback text reply for the *default* command scope (DMs, etc).

    The rich status/switch flow only runs through ``pre_dispatch`` /
    ``GROUP_VISIBLE_COMMANDS`` — group chats need that separate registration
    (see module docstring), so this plain-text path covers everywhere else.
    """
    profiles = _doer.projects
    return "Profiles: " + ", ".join(profiles) if profiles else "No profiles loaded."


def register(ctx) -> None:
    ctx.register_hook("pre_gateway_dispatch", pre_dispatch)
    ctx.register_command(
        COMMAND_PROFILE,
        handler=_default_scope_profile,
        description="Show/switch the active profile",
        args_hint="[name]",
    )
    ctx.register_command(
        COMMAND_PROJECT_ALIAS,
        handler=_default_scope_profile,
        description="Show/switch the active profile (alias for /profile)",
        args_hint="[name]",
    )
    _telegram.register_group_commands(GROUP_VISIBLE_COMMANDS)
    _doer.load()
