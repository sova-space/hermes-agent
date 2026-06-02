import os

import httpx

_agent_commands: set[str] = set()
_commands_loaded = False


def _load_commands() -> None:
    global _commands_loaded
    if _commands_loaded:
        return
    urls = [
        v
        for k, v in os.environ.items()
        if k.startswith("AGENT_") and k.endswith("_URL")
    ]
    for base_url in urls:
        url = base_url.rstrip("/")
        if not url.startswith("http"):
            url = f"https://{url}"
        try:
            resp = httpx.get(f"{url}/bot/commands", timeout=5)
            _agent_commands.update(c["command"] for c in resp.json())
        except Exception:
            pass
    _commands_loaded = True


def pre_dispatch(event, **kwargs):
    _load_commands()
    cmd = event.get_command() if hasattr(event, "get_command") else None
    if not cmd or cmd not in _agent_commands:
        return None
    text = getattr(event, "text", "") or ""
    command_token = text.split()[0] if text else ""
    if "@" in command_token:
        return {"action": "skip", "reason": "agent bot command"}
    return None


def register(ctx) -> None:
    ctx.register_hook("pre_gateway_dispatch", pre_dispatch)
    _load_commands()
