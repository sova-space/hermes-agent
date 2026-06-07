"""Typed extraction of chat/thread identifiers from a Hermes ``MessageEvent``.

Hermes normalizes every platform update into a ``MessageEvent`` whose chat and
topic identifiers live on ``event.source`` (a ``SessionSource``) — *not* on
the event itself, and *not* shaped like a raw python-telegram-bot ``Update``.
``event.chat_id`` / ``event.chat.id`` / ``event.message.chat["id"]`` all
return nothing, silently, because those attributes don't exist.

That exact mistake shipped once: every reply from this plugin's ``/project``
and ``/do`` commands got swallowed because the extracted ``chat_id`` was
always ``None``. Route every chat/thread read through ``ChatContext.from_event``
— never reach into the raw event — so it can't happen again.
"""

from dataclasses import dataclass

# Forum "General" topic sentinel — see thread_id_for_send.
_GENERAL_TOPIC_THREAD_ID = "1"


@dataclass(frozen=True)
class ChatContext:
    """Where a message arrived: which chat, and which forum topic (if any).

    Both ids are plain strings — that's how ``SessionSource`` carries them,
    Telegram's numeric ids included. Don't assume ``int``.
    """

    chat_id: str | None
    thread_id: str | None

    @classmethod
    def from_event(cls, event) -> "ChatContext":
        source = getattr(event, "source", None)
        return cls(
            chat_id=getattr(source, "chat_id", None),
            thread_id=getattr(source, "thread_id", None),
        )

    @property
    def thread_id_for_send(self) -> int | None:
        """Thread id for a Telegram ``sendMessage`` payload, or ``None`` to
        omit ``message_thread_id`` entirely.

        Two cases collapse to ``None``: no topic at all (plain group chat),
        and the forum's "General" topic (id ``"1"``) — Telegram rejects
        ``sendMessage`` calls that set ``message_thread_id=1`` explicitly, so
        the gateway's own Telegram adapter omits it there too (see
        ``_message_thread_id_for_send`` in ``gateway/platforms/telegram.py``
        of NousResearch/hermes-agent). Mirror that, or replies in General
        fail the exact same silent way the missing ``chat_id`` read did.
        """
        if not self.thread_id or self.thread_id == _GENERAL_TOPIC_THREAD_ID:
            return None
        return int(self.thread_id)
