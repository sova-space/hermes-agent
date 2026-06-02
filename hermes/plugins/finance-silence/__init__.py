import asyncio
import os

import httpx

_finance_commands: set[str] = set()


async def _load_commands() -> None:
    base = os.getenv("FINANCE_API_URL", "")
    if not base:
        return
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"https://{base}/bot/commands", timeout=5)
            _finance_commands.update(c["command"] for c in resp.json())
    except Exception:
        pass


async def pre_dispatch(event, **kwargs):
    cmd = event.get_command() if hasattr(event, "get_command") else None
    if cmd and cmd in _finance_commands:
        return {"action": "skip", "reason": "finance bot command"}
    return None


def register(ctx) -> None:
    ctx.register_hook("pre_gateway_dispatch", pre_dispatch)
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(_load_commands())
        else:
            loop.run_until_complete(_load_commands())
    except Exception:
        pass
