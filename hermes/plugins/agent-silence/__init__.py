import os

import httpx

_agent_commands: set[str] = set()
_commands_loaded = False

# Commands Hermes routes to the Doer agent: do_<project>
_DOER_PREFIX = "do_"


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


def _dispatch_doer(event, project: str) -> None:
    """Call Doer API and send an ack message to Telegram."""
    text = getattr(event, "text", "") or ""
    parts = text.split(None, 1)
    task = parts[1].strip() if len(parts) > 1 else ""
    if not task:
        return

    doer_url = os.environ.get("AGENT_DOER_URL", "").rstrip("/")
    if doer_url:
        try:
            httpx.post(f"{doer_url}/task", json={"project": project, "task": task}, timeout=5)
        except Exception:
            pass

    # Ack the user in the same chat/topic.
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = (
        getattr(event, "chat_id", None)
        or getattr(getattr(event, "chat", None), "id", None)
        or getattr(getattr(event, "message", None), "chat", {}).get("id")
    )
    thread_id = (
        getattr(event, "message_thread_id", None)
        or getattr(getattr(event, "message", None), "message_thread_id", None)
    )

    if bot_token and chat_id:
        payload: dict = {
            "chat_id": chat_id,
            "text": f"Got it — Doer is working on `{project}`. Result in #projects.",
            "parse_mode": "Markdown",
        }
        if thread_id:
            payload["message_thread_id"] = thread_id
        try:
            httpx.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json=payload,
                timeout=5,
            )
        except Exception:
            pass


def pre_dispatch(event, **kwargs):
    _load_commands()
    cmd = event.get_command() if hasattr(event, "get_command") else None
    if not cmd:
        return None

    # Route /do_<project> commands to Doer before the framework can reject them.
    if cmd.startswith(_DOER_PREFIX):
        project = cmd[len(_DOER_PREFIX):]
        _dispatch_doer(event, project)
        return {"action": "skip", "reason": "doer command"}

    # Silence commands owned by other bots (only when @-addressed).
    if cmd not in _agent_commands:
        return None
    text = getattr(event, "text", "") or ""
    command_token = text.split()[0] if text else ""
    if "@" in command_token:
        return {"action": "skip", "reason": "agent bot command"}
    return None


def register(ctx) -> None:
    ctx.register_hook("pre_gateway_dispatch", pre_dispatch)
    _load_commands()
