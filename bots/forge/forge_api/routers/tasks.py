"""Task submission and status endpoints."""

import asyncio
import uuid

import structlog
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from forge_api.agent import loop as agent_loop
from forge_api.agent.projects import PROJECTS

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/task")

_background_tasks: set[asyncio.Task] = set()


class TaskRequest(BaseModel):
    """Incoming task from Hermes skill."""

    project: str
    task: str


class TaskResponse(BaseModel):
    """Immediate ack returned to Hermes."""

    task_id: str
    status: str


@router.post("", response_model=TaskResponse)
async def submit_task(body: TaskRequest, request: Request) -> TaskResponse:
    """Accept a task, start it in the background, return task_id immediately."""
    if body.project not in PROJECTS:
        known = ", ".join(PROJECTS)
        raise HTTPException(
            status_code=400,
            detail=f"Unknown project '{body.project}'. Known: {known}",
        )

    task_id = str(uuid.uuid4())[:8]
    task_store: dict = request.app.state.tasks
    task_store[task_id] = {"status": "queued"}

    log.info("task_submitted", task_id=task_id, project=body.project)
    t = asyncio.create_task(
        agent_loop.run(task_id, body.project, body.task, task_store),
        name=f"forge-{task_id}",
    )
    _background_tasks.add(t)
    t.add_done_callback(_background_tasks.discard)

    return TaskResponse(task_id=task_id, status="queued")


@router.get("/{task_id}")
async def get_task(task_id: str, request: Request) -> dict:
    """Return the current status of a task."""
    task_store: dict = request.app.state.tasks
    task = task_store.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task_id": task_id, **task}
