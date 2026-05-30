import json
import urllib.request

FINANCE_API_URL = "https://finance-api-production-4d72.up.railway.app"
FINANCE_THREAD_ID = "1192"


def _on_pre_gateway_dispatch(event, **kwargs):
    thread_id = getattr(getattr(event, "source", None), "thread_id", None)
    text = getattr(event, "text", "") or ""
    if thread_id == FINANCE_THREAD_ID and "@sova_finance_bot" in text:
        print(f"[skip-finance-bot-commands] skipping: {text!r}", flush=True)
        return {"action": "skip", "reason": "command addressed to sova_finance_bot in finance topic"}


def _balance_handler(args: str) -> str:
    try:
        req = urllib.request.Request(f"{FINANCE_API_URL}/accounts")
        with urllib.request.urlopen(req, timeout=10) as resp:
            accounts = json.loads(resp.read())
        if not accounts:
            return "No accounts found. Run /sync@sova_finance_bot first."
        lines = []
        for acc in accounts:
            name = acc.get("name", "Account")
            balance = acc.get("balance", 0)
            currency = acc.get("currency", "UAH")
            lines.append(f"{name}: {balance:,.2f} {currency}")
        return "\n".join(lines)
    except Exception as e:
        return f"Could not fetch balance: {e}"


def register(ctx):
    print("[skip-finance-bot-commands] plugin registered", flush=True)
    ctx.register_hook("pre_gateway_dispatch", _on_pre_gateway_dispatch)
    ctx.register_command(
        "balance",
        handler=_balance_handler,
        description="Show Monobank account balances",
    )
