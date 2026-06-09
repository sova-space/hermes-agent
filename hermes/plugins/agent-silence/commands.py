"""The /profile + /mode command surface, and the pattern for adding more.

``/profile`` is the entry point for picking which domain you're working in,
and ``/mode`` decides how plain text in that profile gets routed (see
``specs/014-profile-router/spec.md`` — the profile router; the mode toggle is
an evolution of its original ``/do``-vs-plain-text design, see below):

- ``/profile`` (no name) — show the chat's active profile (if any) and the
  list of available ones.
- ``/profile <name>`` — make ``<name>`` the chat's active profile (``/project``
  is kept as a backward-compatible alias — same handler, same state). New
  profiles start in ``client`` mode — the safer no-op default.
- ``/mode`` (no name) — show the chat's active mode.
- ``/mode <client|dev>`` — switch how plain-text messages route in the active
  profile.

Once a profile is active, its *mode* decides how a plain-text message (no
leading ``/``) routes — intent is signalled explicitly via the mode switch,
never guessed per-message (spec 014's original ``/do`` design made the same
point with a per-message verb; a sticky mode carries the same explicitness
with less typing):

- ``client`` mode — domain Q&A, routed to the profile-owning bot's own
  conversational assistant (``handle_profile_message`` → ``ask_profile``).
  If no owner is registered for that profile (e.g. ``hermes`` — Hermes *is*
  the orchestrator, it doesn't run a separate domain API), the message falls
  through to ordinary Hermes conversation instead of being forced anywhere.
- ``dev`` mode — the message *is* a devops task description (code change,
  bug fix, …), run against that profile's repo via the absorbed GitHub loop
  (``AgentLoop.dispatch`` — see ``agent_loop.py``). Routing a GitHub-editing
  loop off an LLM's guess at "is this a bug report or a question" is exactly
  the kind of thing that quietly does the wrong thing — ``dev`` mode makes
  that guess the user's, made once via ``/mode dev``, not per message.

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
from .agent_loop import AgentLoop
from .doer import MODE_CLIENT, MODE_DEV, MODES, DoerGateway, DoerSession
from .telegram_client import TelegramClient

# Slash-command names this module owns. Matched against
# ``event.get_command()``, which the gateway already lowercases and strips
# any "@botname" disambiguation suffix from — handlers never see raw text.
COMMAND_PROFILE = "profile"
COMMAND_PROJECT_ALIAS = "project"  # back-compat — same handler, same state
COMMAND_MODE = "mode"
COMMAND_FINANCE = "finance"

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
    devops: AgentLoop
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
    mode = ctx.session.active_mode(ctx.chat.chat_id) if active else "client"
    llm_model = ctx.doer.llm_model
    agent_model = ctx.doer.agent_model
    quick_model = ctx.doer.quick_model

    keyboard = {
        "keyboard": [
            [{"text": f"{p} 💬"}, {"text": f"{p} 🔧"}] for p in profiles
        ],
        "resize_keyboard": True,
        "one_time_keyboard": True,
    }

    active_info = f"Active: *{active}* — mode: *{mode}*" if active else "No profile selected"
    text = (
        f"{active_info}\n\n"
        f"*LLM:* {llm_model}\n"
        f"*Agent:* {agent_model}\n"
        f"*Quick:* {quick_model}\n\n"
        "Select a profile:"
    )
    ctx.telegram.send_message(ctx.chat, text, reply_markup=keyboard)
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

    keyboard = {
        "keyboard": [
            [{"text": "💬 client"}, {"text": "🔧 dev"}],
        ],
        "resize_keyboard": True,
        "one_time_keyboard": True,
    }

    mode = ctx.session.active_mode(ctx.chat.chat_id)
    owner = ctx.doer.profiles.get(name)
    hint = (
        "ask a question and assistant will answer."
        if mode == MODE_CLIENT and owner is not None
        else "ordinary conversation (no assistant for this profile)."
        if mode == MODE_CLIENT
        else "plain messages run as devops tasks against repo."
    )
    ctx.telegram.send_message(
        ctx.chat,
        f"Profile: *{name}* — mode: *{mode}*\n{hint}\n\nSelect mode:",
        reply_markup=keyboard,
    )
    return skip("doer profile selected")


def handle_mode(ctx: CommandContext) -> dict[str, str] | None:
    """``/mode`` — show or switch the active profile's routing mode.

    The explicit, sticky signal that replaced ``/do``-vs-plain-text (see
    module docstring): ``client`` routes plain messages to the profile's
    domain assistant, ``dev`` runs them as devops tasks against its repo.
    Requires an active profile — mode is meaningless without one.
    """
    profile = ctx.session.active_profile(ctx.chat.chat_id)
    if not profile:
        ctx.telegram.send_message(
            ctx.chat, "No active profile. Use `/profile <name>` first."
        )
        return skip("mode no active profile")

    if not ctx.args:
        mode = ctx.session.active_mode(ctx.chat.chat_id)
        ctx.telegram.send_message(
            ctx.chat,
            f"Mode for `{profile}` is *{mode}*. Switch with `/mode client|dev`.",
        )
        return skip("mode status")

    name = ctx.args.split()[0].lower()
    if name not in MODES:
        ctx.telegram.send_message(
            ctx.chat, f"Unknown mode `{name}`. Choose `client` or `dev`."
        )
        return skip("mode unknown")

    ctx.session.set_mode(ctx.chat.chat_id, name)
    hint = (
        f"plain messages now go to `{profile}`'s assistant."
        if name == MODE_CLIENT
        else f"plain messages now run as devops tasks against `{profile}`'s repo "
        "— results land in #projects."
    )
    ctx.telegram.send_message(ctx.chat, f"Mode set to *{name}* — {hint}")
    return skip("mode switched")


def _handle_dev_task(ctx: CommandContext, profile: str, task: str) -> dict[str, str]:
    """``dev``-mode plain message — run it as a devops task on ``profile``'s repo."""
    ctx.devops.dispatch(profile, task)
    ctx.telegram.send_message(
        ctx.chat, f"Got it — Doer is working on `{profile}`. Result in #projects."
    )
    return skip("devops task dispatched")


def handle_profile_message(ctx: CommandContext) -> dict[str, str] | None:
    """Plain-text message (no slash command) in a chat with an active
    profile — routed by the chat's mode (see module docstring):

    - ``client`` → domain Q&A, routed to that profile owner's conversational
      assistant
    - ``dev`` → the message is a devops task description, run against the
      profile's repo via the absorbed GitHub loop

    Also handles custom keyboard taps:
    - Profile names → switch profile
    - \"💬 client\" / \"🔧 dev\" → switch mode

    Returns ``None`` (let the gateway fall through to normal agent dispatch)
    whenever there's nothing this plugin should handle — no active profile,
    no text, ``client`` mode with no assistant registered — those are all
    "ordinary conversation" cases.
    """
    text = ctx.text.strip()
    if not text:
        return None

    # Handle keyboard button taps: "<profile> 💬" or "<profile> 🔧"
    profiles = ctx.doer.projects
    for p in profiles:
        if text == f"{p} 💬":
            ctx.session.select(ctx.chat.chat_id, p)
            ctx.session.set_mode(ctx.chat.chat_id, "client")
            ctx.telegram.send_message(ctx.chat, f"*{p}* · client — ask away.")
            return skip("keyboard profile+mode")
        if text == f"{p} 🔧":
            ctx.session.select(ctx.chat.chat_id, p)
            ctx.session.set_mode(ctx.chat.chat_id, "dev")
            ctx.telegram.send_message(ctx.chat, f"*{p}* · dev — results in #projects.")
            return skip("keyboard profile+mode")

    profile = ctx.session.active_profile(ctx.chat.chat_id)
    if not profile:
        return None
    if ctx.session.active_mode(ctx.chat.chat_id) == MODE_DEV:
        return _handle_dev_task(ctx, profile, text)

    reply = ctx.doer.ask_profile(profile, ctx.chat.chat_id, text)
    if reply is None:
        return None
    ctx.telegram.send_message(ctx.chat, reply)
    return skip("profile assistant replied")


def handle_finance(ctx: CommandContext) -> dict[str, str] | None:
    """``/finance`` — switch to finance profile, show balance + commands."""
    profiles = ctx.doer.projects
    if "finance" not in profiles:
        ctx.telegram.send_message(ctx.chat, "Finance profile is not available.")
        return skip("finance unavailable")

    ctx.session.select(ctx.chat.chat_id, "finance")
    ctx.session.set_mode(ctx.chat.chat_id, "client")

    # Try to get balance from finance bot
    balance_text = ""
    reply = ctx.doer.ask_profile("finance", ctx.chat.chat_id, "/balance")
    if reply:
        balance_text = reply

    keyboard = {
        "keyboard": [
            [{"text": "/balance"}],
            [{"text": "finance 💬"}, {"text": "finance 🔧"}],
        ],
        "resize_keyboard": True,
        "one_time_keyboard": True,
    }

    llm_model = ctx.doer.llm_model
    text = (
        f"💰 *Finance* — profile active\n\n"
        f"{balance_text}\n"
        f"*LLM:* {llm_model}\n\n"
        "Commands:"
    )
    ctx.telegram.send_message(ctx.chat, text, reply_markup=keyboard)
    return skip("finance handler")


# Exact-name command -> handler. See module docstring for how to extend this.
COMMANDS: dict[str, CommandHandler] = {
    COMMAND_PROFILE: handle_profile,
    COMMAND_PROJECT_ALIAS: handle_profile,
    COMMAND_MODE: handle_mode,
    COMMAND_FINANCE: handle_finance,
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
