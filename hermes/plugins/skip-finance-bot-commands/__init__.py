# Commands owned by sub-agents. Hermes stays silent for all of these.
# Add new agent commands here as sub-agents are added to the group.
AGENT_COMMANDS = {"balance", "stats", "budget", "sync"}


def _on_pre_gateway_dispatch(event, **kwargs):
    text = (getattr(event, "text", None) or "").strip()
    if not text.startswith("/"):
        return
    cmd_token = text.split()[0]
    # Drop any command explicitly addressed to another bot (/cmd@anybot)
    if "@" in cmd_token:
        return {"action": "skip", "reason": "Command addressed to another bot"}
    # Drop known sub-agent commands even when typed without a bot target
    cmd_name = cmd_token.lstrip("/").lower()
    if cmd_name in AGENT_COMMANDS:
        return {"action": "skip", "reason": f"/{cmd_name} belongs to a sub-agent"}


def register(ctx):
    ctx.register_hook("pre_gateway_dispatch", _on_pre_gateway_dispatch)
