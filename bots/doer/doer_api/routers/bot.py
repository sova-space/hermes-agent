"""Hermes ecosystem discovery endpoint."""

from fastapi import APIRouter

from doer_api.agent.projects import PROJECTS

router = APIRouter()

BOT_COMMANDS: list[dict] = [
    {"command": "project", "description": "Pick active project for Doer"},
    {"command": "do", "description": "Run a task on the active project via Doer"},
]


@router.get("/bot/commands", include_in_schema=False)
async def bot_commands() -> list[dict]:
    """Return registered bot commands. Hermes fetches this for command ownership."""
    return BOT_COMMANDS


@router.get("/bot/projects", include_in_schema=False)
async def bot_projects() -> list[str]:
    """Return the list of known project slugs. Plugin fetches this for the picker keyboard."""
    return sorted(PROJECTS.keys())
