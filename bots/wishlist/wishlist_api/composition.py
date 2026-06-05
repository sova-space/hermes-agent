"""FastAPI application factory."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from wishlist_api.core.config import settings
from wishlist_api.core.logging.setup import configure_logging
from wishlist_api.domains.bot.commands import setup_bot
from wishlist_api.domains.bot.runner import create_bot
from wishlist_api.routers import health, miniapp

log = structlog.get_logger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    configure_logging(
        level=settings.log_level,
        json=settings.environment != "local",
    )

    bot_app = create_bot(settings.telegram_bot_token)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        await bot_app.initialize()
        await setup_bot(bot_app.bot)
        await bot_app.start()
        await bot_app.updater.start_polling(drop_pending_updates=True)
        log.info("telegram_bot_started")
        try:
            yield
        finally:
            await bot_app.updater.stop()
            await bot_app.stop()
            await bot_app.shutdown()

    app = FastAPI(
        title="Wishlist API",
        version="0.1.0",
        description="Wishlist bot API — public multi-user Telegram wishlist.",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.include_router(health.router)
    app.include_router(miniapp.router)

    return app
