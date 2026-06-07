"""The /project and /do command surface, and the pattern for adding more.

## Adding a new Doer command

1. Write a handler with the signature ``(ctx: CommandContext) -> dict | None``:
   - Reply via ``ctx.telegram.send_message(ctx.chat, ...)`` — never build a
     chat/thread id by hand (see ``chat_context.ChatContext`` for why that
     bit us once).
   - Return ``skip(reason)`` to tell the gateway "handled, don't fall through
     to normal agent dispatch"; return ``None`` to let it fall through.
2. Register it in ``COMMANDS`` (exact-name match). Prefix-style commands like
   ``/do_<project>`` are routed in ``route()`` directly — extend that if you
   need another prefix family.
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
COMMAND_PROJECT = "project"
COMMAND_DO = "do"

# Prefix family for the explicit-project shorthand: /do_<project> <task>
DO_PROJECT_PREFIX = "do_"

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


def handle_pending_selection(ctx: CommandContext) -> dict[str, str] | None:
    """Plain-text reply to the ``/project`` picker keyboard (no slash
    command — the user tapped a button, which Telegram sends as text)."""
    if not ctx.session.is_awaiting_selection(ctx.chat.chat_id):
        return None
    chosen = ctx.text.strip().lower()
    if chosen not in ctx.doer.projects:
        return None
    ctx.session.select(ctx.chat.chat_id, chosen)
    ctx.telegram.send_message(
        ctx.chat,
        f"Project set to *{chosen}*. Use `/do <task>` to run a task.",
        reply_markup={"remove_keyboard": True},
    )
    return skip("doer project selected")


def handle_project(ctx: CommandContext) -> dict[str, str] | None:
    """``/project`` — show the project picker keyboard."""
    projects = ctx.doer.projects
    if not projects:
        ctx.telegram.send_message(ctx.chat, "Doer is unavailable — no projects loaded.")
        return skip("doer project picker unavailable")
    ctx.session.await_selection(ctx.chat.chat_id)
    buttons = [[{"text": project.capitalize()} for project in projects]]
    ctx.telegram.send_message(
        ctx.chat,
        "Select a project:",
        reply_markup={
            "keyboard": buttons,
            "one_time_keyboard": True,
            "resize_keyboard": True,
        },
    )
    return skip("doer project picker")


def handle_do(ctx: CommandContext) -> dict[str, str] | None:
    """``/do <task>`` — dispatch ``<task>`` to the chat's active project."""
    project = ctx.session.active_project(ctx.chat.chat_id)
    if not project:
        ctx.telegram.send_message(
            ctx.chat, "No project selected. Use `/project` to pick one first."
        )
        return skip("no doer project selected")
    if not ctx.args:
        ctx.telegram.send_message(
            ctx.chat,
            f"Active project: *{project}*. Usage: `/do <task description>`",
        )
        return skip("doer no task")
    _dispatch(ctx, project, ctx.args)
    return skip("doer command")


def handle_do_project(ctx: CommandContext, project: str) -> dict[str, str] | None:
    """``/do_<project> <task>`` — explicit-project shorthand; also makes
    ``<project>`` the chat's active project for subsequent plain ``/do``."""
    if ctx.chat.chat_id is not None:
        ctx.session.select(ctx.chat.chat_id, project)
    if not ctx.args:
        return skip("doer no task")
    _dispatch(ctx, project, ctx.args)
    return skip("doer command")


def _dispatch(ctx: CommandContext, project: str, task: str) -> None:
    ctx.doer.dispatch(project, task)
    ctx.telegram.send_message(
        ctx.chat, f"Got it — Doer is working on `{project}`. Result in #projects."
    )


# Exact-name command -> handler. See module docstring for how to extend this.
COMMANDS: dict[str, CommandHandler] = {
    COMMAND_PROJECT: handle_project,
    COMMAND_DO: handle_do,
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
    if cmd.startswith(DO_PROJECT_PREFIX):
        return handle_do_project(ctx, project=cmd[len(DO_PROJECT_PREFIX) :])
    return None
