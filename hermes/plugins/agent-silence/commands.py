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

import os
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import quote

from .agent_loop import AgentLoop
from .chat_context import ChatContext
from .doer import LANGUAGES, MODE_CLIENT, MODE_DEV, MODES, DoerGateway, DoerSession
from .telegram_client import TelegramClient

# Slash-command names this module owns. Matched against
# ``event.get_command()``, which the gateway already lowercases and strips
# any "@botname" disambiguation suffix from — handlers never see raw text.
COMMAND_PROFILE = "profile"
COMMAND_PROJECT_ALIAS = "project"  # back-compat — same handler, same state
COMMAND_MODE = "mode"
COMMAND_FINANCE = "finance"
COMMAND_BALANCE = "balance"
COMMAND_LANGUAGE = "language"

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
    callback_data: str | None = None
    callback_query_id: str | None = None
    callback_message_id: str | int | None = None


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


def _profile_payload(ctx: CommandContext, profiles: list[str]) -> dict:
    active = ctx.session.active_profile(ctx.chat.chat_id)
    mode = ctx.session.active_mode(ctx.chat.chat_id) if active else MODE_CLIENT
    active_line = (
        f"<b>Active:</b> <code>{active}</code> · <b>{mode}</b>"
        if active
        else "<b>Active:</b> none"
    )
    rows = [
        [
            {
                "text": f"{'✅ ' if active == p else ''}{p}",
                "callback_data": f"prof:project:{p}",
            }
            for p in profiles
        ],
        [
            {
                "text": f"{'✅ ' if mode == MODE_CLIENT else ''}💬 client",
                "callback_data": f"prof:mode:{MODE_CLIENT}",
            },
            {
                "text": f"{'✅ ' if mode == MODE_DEV else ''}🔧 dev",
                "callback_data": f"prof:mode:{MODE_DEV}",
            },
        ],
    ]
    text = f"<b>Project router</b>\n{active_line}"
    return {
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": {"inline_keyboard": rows},
    }


def _report_status(ctx: CommandContext, profiles: list[str]) -> dict[str, str]:
    payload = _profile_payload(ctx, profiles)
    ctx.telegram.send_message(
        ctx.chat,
        payload["text"],
        reply_markup=payload["reply_markup"],
        parse_mode=payload["parse_mode"],
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

    payload = _profile_payload(ctx, profiles)
    ctx.telegram.send_message(
        ctx.chat,
        payload["text"],
        reply_markup=payload["reply_markup"],
        parse_mode=payload["parse_mode"],
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


def _language_payload(chat_id: str | None, session: DoerSession) -> dict:
    current = session.active_language(chat_id)
    rows = [
        [
            {
                "text": f"{'✅ ' if current == code else ''}{name}",
                "callback_data": f"lang:{code}",
            }
            for code, name in LANGUAGES.items()
        ]
    ]
    return {
        "text": "<b>Language</b>",
        "parse_mode": "HTML",
        "reply_markup": {"inline_keyboard": rows},
    }


def _push_language_to_services(ctx: CommandContext, language: str) -> None:
    import httpx

    for base_url in ctx.doer._discover_agent_urls():
        url = ctx.doer._normalize(base_url)
        try:
            httpx.put(f"{url}/bot/language", json={"language": language}, timeout=5)
        except Exception:
            pass


def handle_language(ctx: CommandContext) -> dict[str, str] | None:
    """``/language`` — general language selector for every service."""
    if ctx.args:
        if ctx.chat.chat_id is None:
            return skip("language no chat")
        selected = ctx.args.split()[0].lower()
        if selected not in LANGUAGES:
            ctx.telegram.send_message(ctx.chat, "Unknown language. Choose en or uk.")
            return skip("language unknown")
        ctx.session.set_language(ctx.chat.chat_id, selected)
        _push_language_to_services(ctx, selected)

    payload = _language_payload(ctx.chat.chat_id, ctx.session)
    ctx.telegram.send_message(
        ctx.chat,
        payload["text"],
        reply_markup=payload["reply_markup"],
        parse_mode=payload["parse_mode"],
    )
    return skip("language")


def handle_language_callback(ctx: CommandContext) -> dict[str, str] | None:
    data = ctx.callback_data
    if not data or not data.startswith("lang:"):
        return None
    selected = data[len("lang:") :]
    if selected not in LANGUAGES:
        ctx.telegram.answer_callback_query(ctx.callback_query_id)
        return skip("language unknown callback")
    ctx.telegram.answer_callback_query(ctx.callback_query_id)
    if ctx.chat.chat_id is None:
        return skip("language no chat callback")
    ctx.session.set_language(ctx.chat.chat_id, selected)
    _push_language_to_services(ctx, selected)
    payload = _language_payload(ctx.chat.chat_id, ctx.session)
    if ctx.callback_message_id is None:
        ctx.telegram.send_message(
            ctx.chat,
            payload["text"],
            reply_markup=payload["reply_markup"],
            parse_mode=payload["parse_mode"],
        )
    else:
        ctx.telegram.edit_message_text(
            ctx.chat,
            ctx.callback_message_id,
            payload["text"],
            reply_markup=payload["reply_markup"],
            parse_mode=payload["parse_mode"],
        )
    return skip("language callback")


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
        if profile == "hermes":
            return None
        ctx.telegram.send_message(
            ctx.chat,
            f"{profile} assistant is unavailable. Try again in a moment.",
            parse_mode="Markdown",
        )
        return skip("profile assistant unavailable")
    ctx.telegram.send_message(ctx.chat, reply)
    return skip("profile assistant replied")


_FINANCE_CALLBACK_VIEW = {
    "balance_cb": "balance",
    "income": "income",
    "spending": "spending",
    "subs": "subs",
    "skipped": "skipped",
}
_FINANCE_SYNC_CALLBACK = "sync"
_FINANCE_SPENDING_PREFIX = "spd:"


def _finance_base_url() -> str:
    """Finance API base URL; AGENT_FINANCE_URL is the profile-router source of truth."""
    url = os.environ.get("AGENT_FINANCE_URL") or os.environ.get("FINANCE_API_URL", "")
    url = url.rstrip("/")
    return url if url.startswith("http") else f"https://{url}" if url else ""


def _finance_payload(path: str, method: str = "GET") -> dict | None:
    """Fetch a Telegram-ready UI payload from finance_api's /bot/ui endpoints."""
    import httpx

    base_url = _finance_base_url()
    if not base_url:
        return None
    try:
        if method == "POST":
            resp = httpx.post(f"{base_url}{path}", timeout=10)
        else:
            resp = httpx.get(f"{base_url}{path}", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _send_finance_payload(ctx: CommandContext, payload: dict | None) -> dict[str, str]:
    if not payload:
        ctx.telegram.send_message(ctx.chat, "Could not fetch finance UI.")
        return skip("finance ui fetch failed")
    ctx.telegram.send_message(
        ctx.chat,
        payload.get("text", ""),
        reply_markup=payload.get("reply_markup"),
        parse_mode=payload.get("parse_mode", "HTML"),
    )
    return skip("finance ui")


def _edit_finance_payload(ctx: CommandContext, payload: dict | None) -> dict[str, str]:
    ctx.telegram.answer_callback_query(ctx.callback_query_id)
    if not payload:
        ctx.telegram.send_message(ctx.chat, "Could not fetch finance UI.")
        return skip("finance callback fetch failed")
    if ctx.callback_message_id is None:
        return _send_finance_payload(ctx, payload)
    ctx.telegram.edit_message_text(
        ctx.chat,
        ctx.callback_message_id,
        payload.get("text", ""),
        reply_markup=payload.get("reply_markup"),
        parse_mode=payload.get("parse_mode", "HTML"),
    )
    return skip("finance callback")


def handle_finance(ctx: CommandContext) -> dict[str, str] | None:
    """``/finance`` — show the finance_api one-message inline UI."""
    return _send_finance_payload(ctx, _finance_payload("/bot/ui/finance"))


def handle_finance_callback(ctx: CommandContext) -> dict[str, str] | None:
    """Inline finance buttons — edit the same Telegram message in place."""
    data = ctx.callback_data
    if not data:
        return None
    if data == _FINANCE_SYNC_CALLBACK:
        return _edit_finance_payload(
            ctx, _finance_payload("/bot/ui/finance/sync", method="POST")
        )
    if data.startswith(_FINANCE_SPENDING_PREFIX):
        category = data[len(_FINANCE_SPENDING_PREFIX) :]
        path = f"/bot/ui/finance/spending/{quote(category, safe='')}"
        return _edit_finance_payload(ctx, _finance_payload(path))
    view = _FINANCE_CALLBACK_VIEW.get(data)
    if view is None:
        return None
    return _edit_finance_payload(ctx, _finance_payload(f"/bot/ui/finance/{view}"))


# Back-compat: /balance in the Hermes bot opens the same UI, but /finance is the menu entry.
def handle_balance(ctx: CommandContext) -> dict[str, str] | None:
    return handle_finance(ctx)


# Exact-name command -> handler. See module docstring for how to extend this.
COMMANDS: dict[str, CommandHandler] = {
    COMMAND_PROFILE: handle_profile,
    COMMAND_PROJECT_ALIAS: handle_profile,
    COMMAND_MODE: handle_mode,
    COMMAND_LANGUAGE: handle_language,
    COMMAND_FINANCE: handle_finance,
    COMMAND_BALANCE: handle_balance,
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
