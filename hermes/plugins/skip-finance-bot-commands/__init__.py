FINANCE_COMMANDS = {"balance", "stats", "budget", "sync"}


def _on_pre_gateway_dispatch(event, **kwargs):
    text = (getattr(event, "text", None) or "").strip()
    if text.startswith("/"):
        cmd_name = text.split()[0].lstrip("/").lower()
        if cmd_name in FINANCE_COMMANDS:
            return {"action": "skip", "reason": f"/{cmd_name} belongs to @sova_finance_bot"}


def register(ctx):
    ctx.register_hook("pre_gateway_dispatch", _on_pre_gateway_dispatch)
