"""Test that the /sync handler offloads run_sync via asyncio.to_thread (Bug #2)."""

import asyncio
import inspect
from unittest.mock import AsyncMock, MagicMock, patch


def test_sync_handler_is_coroutine() -> None:
    """The sync handler must be an async def."""
    from finance_api.domains.bot.handlers import sync

    assert asyncio.iscoroutinefunction(sync), "sync handler must be async def"


async def test_sync_handler_calls_run_sync_via_to_thread() -> None:
    """run_sync must be called via asyncio.to_thread, not called directly."""
    from finance_api.domains.bot.handlers import sync

    update = MagicMock()
    update.message.reply_html = AsyncMock()
    ctx = MagicMock()

    with (
        patch(
            "finance_api.domains.bot.handlers.asyncio.to_thread",
            new_callable=AsyncMock,
        ) as mock_to_thread,
        patch("finance_api.domains.bot.handlers.get_sync_health", return_value={}),
        patch("finance_api.domains.bot.handlers.format_sync_status", return_value="ok"),
    ):
        await sync(update, ctx)

    mock_to_thread.assert_called_once()
    # First positional argument must be run_sync
    from finance_api.domains.sync.monobank import run_sync

    assert mock_to_thread.call_args.args[0] is run_sync


def test_sync_handler_source_uses_to_thread() -> None:
    """Static check: handler source contains 'asyncio.to_thread'."""
    from finance_api.domains.bot.handlers import sync

    source = inspect.getsource(sync)
    assert "asyncio.to_thread" in source, (
        "sync handler must use asyncio.to_thread to avoid blocking the event loop"
    )
