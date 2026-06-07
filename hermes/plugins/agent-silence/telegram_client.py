"""Thin wrapper around the raw Telegram Bot API for this plugin.

Plugins run inside the shared Hermes gateway process and only have
``httpx``/stdlib available — ``python-telegram-bot`` is a per-bot-service
dependency (see ``bots/finance``, ``bots/wishlist``), not a gateway one. So
every Telegram call here is plain ``httpx`` POSTing JSON dicts that match the
Bot API schema, and ``TelegramClient`` is the single chokepoint that owns the
URL shape, token guard, and error-swallowing contract — add a new Bot API
method as a method here, never as a one-off ``httpx.post`` elsewhere.
"""

from dataclasses import dataclass

import httpx

from .chat_context import ChatContext

_API_URL = "https://api.telegram.org/bot{token}/{method}"

# Command-scope type understood by Telegram's setMyCommands. Hermes registers
# commands only in the default scope, and Telegram does not surface
# default-scope commands inside group chats — only scopes set explicitly for
# groups (all_group_chats / chat) appear there. Without pushing here too,
# group-chat commands like /project and /do stay invisible in chats such as
# Sova Space.
SCOPE_ALL_GROUP_CHATS = "all_group_chats"


@dataclass(frozen=True)
class BotCommand:
    """One entry of a ``setMyCommands`` payload — Telegram's Bot API JSON
    shape, not ``python-telegram-bot``'s typed ``BotCommand`` (unavailable
    here, see module docstring)."""

    command: str
    description: str

    def to_payload(self) -> dict[str, str]:
        return {"command": self.command, "description": self.description}


class TelegramClient:
    """Talks to one bot's Telegram Bot API, given its token."""

    def __init__(self, token: str):
        self._token = token

    def send_message(
        self,
        chat: ChatContext,
        text: str,
        reply_markup: dict | None = None,
    ) -> None:
        """Send ``text`` to ``chat``, replying in its forum topic if any.

        No-ops when ``chat.chat_id`` is ``None`` — that means the chat
        couldn't be resolved (see ``ChatContext``), and Telegram would just
        reject a ``chat_id``-less payload anyway.
        """
        if not chat.chat_id:
            return
        payload: dict = {
            "chat_id": chat.chat_id,
            "text": text,
            "parse_mode": "Markdown",
        }
        thread_id = chat.thread_id_for_send
        if thread_id is not None:
            payload["message_thread_id"] = thread_id
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        self._call("sendMessage", payload)

    def register_group_commands(self, commands: list[BotCommand]) -> None:
        """Push ``commands`` into the ``all_group_chats`` scope so they show
        up in Telegram's ``/`` menu inside group chats (see
        ``SCOPE_ALL_GROUP_CHATS`` for why this scope specifically)."""
        self._call(
            "setMyCommands",
            {
                "commands": [c.to_payload() for c in commands],
                "scope": {"type": SCOPE_ALL_GROUP_CHATS},
            },
        )

    def _call(self, method: str, payload: dict) -> None:
        if not self._token:
            return
        try:
            httpx.post(
                _API_URL.format(token=self._token, method=method),
                json=payload,
                timeout=5,
            )
        except Exception:
            pass
