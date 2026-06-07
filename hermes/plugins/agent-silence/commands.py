"""The /project command surface, and the pattern for adding more.

``/project`` does double duty:

- ``/project`` (no name) — show the chat's active project (if any) and the
  list of available ones.
- ``/project <name>`` — make ``<name>`` the chat's active project. From then
  on, every plain-text message in that chat (no leading ``/``) is dispatched
  to it as a Doer task — see ``handle_active_project_task``. No separate
  ``/do`` command needed; switching projects is just ``/project <name>``
  again.

Every reply that touches the active project restates its name (e.g. "Doer is
working on `hermes`") — in a busy group chat it's easy to lose track of which
project plain messages are now being routed to, and a silent mode is exactly
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

# The one slash-command name this module owns. Matched against
# ``event.get_command()``, which the gateway already lowercases and strips
# any "@botname" disambiguation suffix from — handlers never see raw text.
COMMAND_PROJECT = "project"

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


def handle_project(ctx: CommandContext) -> dict[str, str] | None:
    """``/project`` — show active project + choices, or switch to one.

    ``/project`` alone reports status; ``/project <name>`` switches (the
    first whitespace-delimited token is the name — anything after it is
    ignored, since selecting and dispatching are deliberately separate
    steps; send the task as a follow-up plain message).
    """
    projects = ctx.doer.projects
    if not projects:
        ctx.telegram.send_message(ctx.chat, "Doer is unavailable — no projects loaded.")
        return skip("doer projects unavailable")

    if not ctx.args:
        return _report_status(ctx, projects)
    return _switch_project(ctx, projects, name=ctx.args.split()[0].lower())


def _report_status(ctx: CommandContext, projects: list[str]) -> dict[str, str]:
    active = ctx.session.active_project(ctx.chat.chat_id)
    headline = f"Active project: *{active}*." if active else "No project selected."
    ctx.telegram.send_message(
        ctx.chat,
        f"{headline}\nAvailable: {', '.join(projects)}.\nUse `/project <name>` to switch.",
    )
    return skip("doer project status")


def _switch_project(
    ctx: CommandContext, projects: list[str], name: str
) -> dict[str, str]:
    if name not in projects:
        ctx.telegram.send_message(
            ctx.chat, f"Unknown project `{name}`. Available: {', '.join(projects)}."
        )
        return skip("doer unknown project")
    ctx.session.select(ctx.chat.chat_id, name)
    ctx.telegram.send_message(
        ctx.chat,
        f"Project set to *{name}*. Send a plain message to run it as a task on `{name}`.",
    )
    return skip("doer project selected")


def handle_active_project_task(ctx: CommandContext) -> dict[str, str] | None:
    """Plain-text message (no slash command) in a chat with an active
    project — dispatch it to that project as a Doer task.

    Returns ``None`` (let the gateway fall through to normal agent dispatch)
    when there's no active project or no chat to key it by — that's the
    "ordinary conversation" case, not a task.
    """
    project = ctx.session.active_project(ctx.chat.chat_id)
    if not project:
        return None
    task = ctx.text.strip()
    if not task:
        return None
    _dispatch(ctx, project, task)
    return skip("doer task dispatched")


def _dispatch(ctx: CommandContext, project: str, task: str) -> None:
    ctx.doer.dispatch(project, task)
    ctx.telegram.send_message(
        ctx.chat, f"Got it — Doer is working on `{project}`. Result in #projects."
    )


# Exact-name command -> handler. See module docstring for how to extend this.
COMMANDS: dict[str, CommandHandler] = {
    COMMAND_PROJECT: handle_project,
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
