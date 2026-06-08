"""Mini App HTML endpoint and bot trigger."""

import os

from fastapi import APIRouter
from fastapi.responses import FileResponse
from pydantic import BaseModel

from finance_api.domains.assistant.loop import answer as assistant_answer
from finance_api.domains.bot.commands import BOT_COMMANDS
from finance_api.domains.bot.notifications import send_finance_app_button

router = APIRouter()

_PROFILE = {
    "name": "finance",
    "description": "Money questions — balances, spending, budgets, transactions.",
    "dispatch_path": "/bot/assistant",
}


class AssistantRequest(BaseModel):
    """A domain question routed here from the profile router."""

    chat_id: int
    text: str


class AssistantResponse(BaseModel):
    """The assistant's answer, sent back to the router for delivery."""

    reply: str


_STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")


@router.get("/miniapp", include_in_schema=False)
async def miniapp() -> FileResponse:
    """Serve the Telegram Mini App HTML shell."""
    path = os.path.join(_STATIC_DIR, "miniapp.html")
    return FileResponse(path, media_type="text/html")


@router.post("/bot/open", include_in_schema=False)
async def bot_open() -> dict:
    """Send the Mini App button to the #finance topic. Called by Hermes skill."""
    send_finance_app_button()
    return {"ok": True}


@router.get("/bot/commands", include_in_schema=False)
async def bot_commands() -> list[dict]:
    """Return registered bot commands. Hermes fetches this to stay in sync."""
    return [{"command": c.command, "description": c.description} for c in BOT_COMMANDS]


@router.get("/bot/profile", include_in_schema=False)
async def bot_profile() -> dict:
    """Profile-router registration.

    Hermes discovers this to route domain Q&A here when `finance` is the
    active profile — see spec 014.
    """
    return _PROFILE


@router.post("/bot/assistant", include_in_schema=False)
async def bot_assistant(request: AssistantRequest) -> AssistantResponse:
    """Answer a free-form money question via the conversational assistant.

    `dispatch_path` target for the `finance` profile — Hermes posts here
    instead of running its own devops loop when the question is domain Q&A,
    not a code-change request.
    """
    reply = await assistant_answer(request.chat_id, request.text)
    return AssistantResponse(reply=reply)
