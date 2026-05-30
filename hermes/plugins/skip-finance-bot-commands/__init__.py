def _on_pre_gateway_dispatch(event, **kwargs):
    text = getattr(event, "text", "") or ""
    if "@sova_finance_bot" in text:
        return {"action": "skip", "reason": "command addressed to sova_finance_bot"}


def register(ctx):
    ctx.register_hook("pre_gateway_dispatch", _on_pre_gateway_dispatch)
