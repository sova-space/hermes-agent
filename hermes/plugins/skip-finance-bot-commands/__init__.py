import json
import urllib.request
from typing import Optional

FINANCE_API_URL = "https://finance-api-production-4d72.up.railway.app"
FINANCE_THREAD_ID = "1192"

# Set by pre_gateway_dispatch so the command handler knows which topic fired.
# Single-user agent — no concurrency concern.
_current_thread_id: Optional[str] = None


def _on_pre_gateway_dispatch(event, **kwargs):
    global _current_thread_id
    _current_thread_id = getattr(getattr(event, "source", None), "thread_id", None)


def _balance_handler(args: str) -> Optional[str]:
    if _current_thread_id != FINANCE_THREAD_ID:
        return None
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
            symbol = {"UAH": "₴", "USD": "$", "EUR": "€"}.get(currency, currency)
            lines.append(f"{name}: {symbol}{balance:,.2f}")
        return "\n".join(lines)
    except Exception as e:
        return f"Could not fetch balance: {e}"


def register(ctx):
    print("[finance-commands] plugin registered", flush=True)
    ctx.register_hook("pre_gateway_dispatch", _on_pre_gateway_dispatch)
    ctx.register_command(
        "balance",
        handler=_balance_handler,
        description="Show Monobank account balances (finance topic only)",
    )
