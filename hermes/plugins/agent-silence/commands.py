"""The /profile command surface, and the pattern for adding more.

``/profile`` is the single entry point for picking which domain you're
working in (see ``specs/014-profile-router/spec.md`` — the profile router):

- ``/profile`` (no name) — show the chat's active profile (if any) and the
  list of available ones.
- ``/profile <name>`` — make ``<name>`` the chat's active profile (``/project``
  is kept as a backward-compatible alias — same handler, same state).

Once a profile is active, two distinct things route two different ways —
intent is signalled explicitly, never guessed:

- ``/do <task>`` — runs a devops task (code change, bug fix, …) against that
  profile's repo, via Doer's generic GitHub loop. Explicit because routing a
  GitHub-editing loop off an LLM's guess at "is this a bug report or a
  question" is exactly the kind of thing that quietly does the wrong thing.
- a plain-text message (no leading ``/``) — domain Q&A, routed to the
  profile-owning bot's own conversational assistant (``handle_profile_message``).
  If no owner is registered for that profile (e.g. ``hermes`` — Hermes *is*
  the orchestrator, it doesn't run a separate domain API), the message falls
  through to ordinary Hermes conversation instead of being forced anywhere.

Every reply that touches the active profile restates its name (e.g. "Doer is
working on `hermes`") — in a busy group chat it's easy to lose track of which
profile plain messages are now being routed to, and a silent mode is exactly
the kind of thing that produces "wait, why did it do that?" later.

## Adding a new command

1. Write a handler with the signature ``(ctx: CommandContext) -> dict | None``:
   - Reply via ``ctx.telegram.send_message(ctx.chat, ...)`` — never build a
     chat/thread id by hand (see ``chat_context.ChatContext`` for why that
     bit us once).
   - Return ``skip(reason)`` to tell the gateway "handled, don't fall through
     to normal agent dispatch"; return ``None`` to let it.
2. Register it in ``COMMANDS`` (exact-name match).
3. If the command should appear in Telegram's ``/`` menu *inside group
   chats*, add a ``BotCommand`` to ``GROUP_VISIBLE_COMMANDS`` in
   ``__init__.py``. That's a separate registration path (the
   ``all_group_chats`` scope) from ``ctx.register_command`` — group chats
   don't surface default-scope commands at all, so skipping this step makes
   the command invisible there even though it works when typed.

``CommandContext`` bundles everything a handler needs precisely so handlers
never reach into the raw ``MessageEvent`` — that's the chokepoint that keeps
the chat_id bug from coming back.
"""

from collections.abc import Callable
from dataclasses import dataclass

from .chat_context import ChatContext
from .doer import DoerGateway, DoerSession
from .telegram_client import TelegramClient

# Slash-command names this module owns. Matched against
# ``event.get_command()``, which the gateway already lowercases and strips
# any "@botname" disambiguation suffix from — handlers never see raw text.
COMMAND_PROFILE = "profile"
COMMAND_PROJECT_ALIAS = "project"  # back-compat — same handler, same state
COMMAND_DO = "do"

# Hook return action telling the gateway "handled — stop here, don't fall
# through to normal agent dispatch". See pre_gateway_dispatch in
# website/docs/user-guide/features/hooks.md for the contract.
_ACTION_SKIP = "skip"


def skip(reason: str) -> dict[str, str]:
    """Build the ``pre_gateway_dispatch`` "handled, stop here" result."""
    return {"action": _ACTION_SKIP, "reason": reason}


@dataclass(frozen=True)
class CommandContext:
    """Everything a command handler needs, bundled so it never has to touch
    the raw ``MessageEvent`` directly."""

    chat: ChatContext
    text: str
    args: str
    telegram: TelegramClient
    doer: DoerGateway
    session: DoerSession


CommandHandler = Callable[[CommandContext], dict[str, str] | None]


def handle_profile(ctx: CommandContext) -> dict[str, str] | None:
    """``/profile`` (or its ``/project`` alias) — show active profile +
    choices, or switch to one.

    Bare form reports status; ``/profile <name>`` switches (the first
    whitespace-delimited token is the name — anything after it is ignored,
    since selecting and dispatching are deliberately separate steps: follow
    up with ``/do <task>`` for devops or a plain message for domain Q&A).
    """
    profiles = ctx.doer.projects
    if not profiles:
        ctx.telegram.send_message(ctx.chat, "Doer is unavailable — no profiles loaded.")
        return skip("doer profiles unavailable")

    if not ctx.args:
        return _report_status(ctx, profiles)
    return _switch_profile(ctx, profiles, name=ctx.args.split()[0].lower())


def _report_status(ctx: CommandContext, profiles: list[str]) -> dict[str, str]:
    active = ctx.session.active_profile(ctx.chat.chat_id)
    headline = f"Active profile: *{active}*." if active else "No profile selected."
    ctx.telegram.send_message(
        ctx.chat,
        f"{headline}\nAvailable: {', '.join(profiles)}.\n"
        "Use `/profile <name>` to switch, `/do <task>` for devops, "
        "or just ask a question.",
    )
    return skip("doer profile status")


def _switch_profile(
    ctx: CommandContext, profiles: list[str], name: str
) -> dict[str, str]:
    if name not in profiles:
        ctx.telegram.send_message(
            ctx.chat, f"Unknown profile `{name}`. Available: {', '.join(profiles)}."
        )
        return skip("doer unknown profile")
    ctx.session.select(ctx.chat.chat_id, name)
    owner = ctx.doer.profiles.get(name)
    hint = (
        f"Ask a question and `{name}`'s assistant will answer, "
        f"or `/do <task>` to change its code."
        if owner is not None
        else f"Send `/do <task>` to run a devops task on `{name}`."
    )
    ctx.telegram.send_message(ctx.chat, f"Profile set to *{name}*. {hint}")
    return skip("doer profile selected")


def handle_devops_task(ctx: CommandContext) -> dict[str, str] | None:
    """``/do <task>`` — run a devops task against the active profile's repo.

    Explicit verb, not inferred from plain text — see module docstring for
    why guessing "is this a bug report or a question" from an LLM is exactly
    the kind of thing that quietly misroutes.
    """
    profile = ctx.session.active_profile(ctx.chat.chat_id)
    if not profile:
        ctx.telegram.send_message(
            ctx.chat, "No active profile. Use `/profile <name>` first."
        )
        return skip("devops no active profile")
    task = ctx.args.strip()
    if not task:
        ctx.telegram.send_message(
            ctx.chat, "Usage: `/do <task>` — e.g. `/do fix the balance rounding bug`."
        )
        return skip("devops missing task")
    ctx.doer.dispatch(profile, task)
    ctx.telegram.send_message(
        ctx.chat, f"Got it — Doer is working on `{profile}`. Result in #projects."
    )
    return skip("devops task dispatched")


def handle_profile_message(ctx: CommandContext) -> dict[str, str] | None:
    """Plain-text message (no slash command) in a chat with an active
    profile — domain Q&A, routed to that profile owner's conversational
    assistant.

    Returns ``None`` (let the gateway fall through to normal agent dispatch)
    when there's no active profile, no text, or no assistant registered for
    the active profile — those are all "ordinary conversation" cases, not
    domain questions this plugin can answer.
    """
    profile = ctx.session.active_profile(ctx.chat.chat_id)
    if not profile:
        return None
    text = ctx.text.strip()
    if not text:
        return None
    reply = ctx.doer.ask_profile(profile, ctx.chat.chat_id, text)
    if reply is None:
        return None
    ctx.telegram.send_message(ctx.chat, reply)
    return skip("profile assistant replied")


# Exact-name command -> handler. See module docstring for how to extend this.
COMMANDS: dict[str, CommandHandler] = {
    COMMAND_PROFILE: handle_profile,
    COMMAND_PROJECT_ALIAS: handle_profile,
    COMMAND_DO: handle_devops_task,
}


def route(cmd: str, ctx: CommandContext) -> dict[str, str] | None:
    """Dispatch a parsed command name to its handler.

    Returns ``None`` when no handler in this module owns ``cmd`` — the
    caller then knows to consider other ownership (e.g. silencing another
    agent's command), not "command failed".
    """
    handler = COMMANDS.get(cmd)
    if handler is not None:
        return handler(ctx)
    return None
