import os

import httpx

_finance_commands: set[str] = set()
_commands_loaded = False


def _load_commands() -> None:
    global _commands_loaded
    if _commands_loaded:
        return
    base = os.getenv("FINANCE_API_URL", "")
    if not base:
        return
    try:
        resp = httpx.get(f"https://{base}/bot/commands", timeout=5)
        _finance_commands.update(c["command"] for c in resp.json())
        _commands_loaded = True
    except Exception:
        pass


def pre_dispatch(event, **kwargs):
    _load_commands()
    cmd = event.get_command() if hasattr(event, "get_command") else None
    if cmd and cmd in _finance_commands:
        return {"action": "skip", "reason": "finance bot command"}
    return None


def register(ctx) -> None:
    ctx.register_hook("pre_gateway_dispatch", pre_dispatch)
    _load_commands()
