"""FastAPI application factory."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from doer_api.routers import bot, health, tasks

structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ],
)

log = structlog.get_logger(__name__)

_DESCRIPTION = "Autonomous developer agent — creates and merges PRs from tasks."


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        app.state.tasks = {}
        log.info("doer_started")
        try:
            yield
        finally:
            log.info("doer_stopped")

    app = FastAPI(
        title="Doer API",
        version="0.1.0",
        description=_DESCRIPTION,
        lifespan=lifespan,
    )

    app.include_router(health.router)
    app.include_router(bot.router)
    app.include_router(tasks.router)

    return app
