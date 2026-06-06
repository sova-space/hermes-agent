"""Send messages to Telegram via the Doer bot."""

import httpx
import structlog

from doer_api.core.config import settings

log = structlog.get_logger(__name__)

_TELEGRAM_API = "https://api.telegram.org"


async def send_to_projects(text: str) -> None:
    """Send a message to the #projects topic."""
    url = f"{_TELEGRAM_API}/bot{settings.doer_bot_token}/sendMessage"
    payload = {
        "chat_id": settings.telegram_chat_id,
        "message_thread_id": settings.telegram_projects_topic_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(url, json=payload)
        if not resp.is_success:
            log.warning(
                "telegram_send_failed",
                status=resp.status_code,
                body=resp.text,
            )
