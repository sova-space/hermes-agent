"""Format Finance API data as Telegram HTML messages."""

from datetime import UTC, date, datetime
from typing import Any

from finance_api.domains.transactions import categories as cat

CATEGORY_EMOJI: dict[str, str] = {
    cat.FOOD_AND_DRINK: "🍔",
    cat.GROCERIES: "🛒",
    cat.TRANSPORTATION: "🚇",
    cat.HEALTHCARE: "💊",
    cat.SHOPPING: "🛍️",
    cat.ENTERTAINMENT: "🎮",
    cat.TRAVEL: "✈️",
    cat.SUBSCRIPTIONS: "📱",
    cat.UTILITIES: "⚡",
    cat.ATM_CASH: "🏧",
    cat.FINANCE: "💳",
    cat.EDUCATION: "🎓",
    cat.PETS: "🐾",
    cat.CASHBACK: "💰",
    cat.INCOME: "💰",
    cat.COUPLE_TRANSFER: "💸",
}

# Currencies where the symbol goes before the amount (e.g. $1,234)
_PREFIX_CURRENCIES = {"USD", "EUR", "GBP"}
CURRENCY_SYMBOL: dict[str, str] = {"UAH": "₴", "USD": "$", "EUR": "€", "GBP": "£"}

_PERIOD_LABEL: dict[str, str] = {
    "this_month": date.today().strftime("%B %Y"),
    "last_month": "last month",
    "last_7d": "last 7 days",
    "last_30d": "last 30 days",
    "last_90d": "last 90 days",
}


def _emoji(category: str) -> str:
    return CATEGORY_EMOJI.get(category, "📦")


def _sym(currency: str) -> str:
    return CURRENCY_SYMBOL.get(currency, currency)


def _fmt_amount(amount: float, currency: str) -> str:
    """Format an amount with the correct currency symbol position and precision."""
    sym = _sym(currency)
    # Use integers for whole amounts, two decimals otherwise
    formatted = f"{amount:,.0f}" if amount == int(amount) else f"{amount:,.2f}"
    if currency in _PREFIX_CURRENCIES:
        return f"{sym}{formatted}"
    return f"{formatted} {sym}"


def _fmt_ago(iso: str | None) -> str:
    """Return a human-readable 'N min ago' / 'N hours ago' string."""
    if not iso:
        return "never"
    dt = datetime.fromisoformat(iso)
    # Normalise both sides to UTC-aware for a safe subtraction.
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    delta = datetime.now(UTC) - dt
    total_minutes = int(delta.total_seconds() // 60)
    if total_minutes < 1:
        return "just now"
    if total_minutes < 60:
        return f"{total_minutes} min ago"
    hours = total_minutes // 60
    return f"{hours} hour{'s' if hours != 1 else ''} ago"


def format_balance(accounts: list[dict[str, Any]]) -> str:
    """Format account balances as HTML."""
    if not accounts:
        return "No accounts synced yet. Run /sync first."
    lines = []
    for a in accounts:
        bal = a["balance"]
        currency = a["currency"]
        name = a["name"]
        lines.append(f"💳 {name}: {bal:,.2f} {currency}")
    lines.append("─────────────")
    latest_sync = max(
        (a["synced_at"] for a in accounts if a.get("synced_at")),
        default=None,
    )
    lines.append(f"Last synced: {_fmt_ago(latest_sync)}")
    return "\n".join(lines)


def format_stats(spending: dict[str, float], period: str = "this_month") -> str:
    """Format spending breakdown as HTML."""
    if not spending:
        return f"No spending data for {_PERIOD_LABEL.get(period, period)}."
    total = sum(spending.values())
    label = _PERIOD_LABEL.get(period, period)
    lines = [f"<b>📊 Spending — {label}</b>", ""]
    for category_name, amount in sorted(
        spending.items(), key=lambda x: x[1], reverse=True
    ):
        pct = round(amount / total * 100) if total else 0
        em = _emoji(category_name)
        lines.append(f"{em} <b>{category_name}</b>  {amount:,.0f} ₴  <i>{pct}%</i>")
    lines += ["", f"<b>Total: {total:,.0f} ₴</b>"]
    return "\n".join(lines)


def format_budget(budgets: list[dict[str, Any]]) -> str:
    """Format budget limits vs spending as HTML."""
    label = date.today().strftime("%B %Y")
    if not budgets:
        return (
            f"<b>📉 Budget — {label}</b>\n\n"
            "No limits set yet.\n"
            "Use <code>/budget set &lt;category&gt; &lt;amount&gt;</code> to add one."
        )
    lines = [f"<b>📉 Budget — {label}</b>", ""]
    for b in budgets:
        em = _emoji(b["category"])
        spent = b["spent"]
        limit = b["monthly_limit"]
        sym = _sym(b["currency"])
        if b["exceeded"]:
            over = spent - limit
            lines.append(
                f"{em} <b>{b['category']}</b>  {spent:,.0f} / {limit:,.0f} {sym}  "
                f"⚠️ <i>over by {over:,.0f}</i>"
            )
        else:
            left = b["remaining"]
            lines.append(
                f"{em} <b>{b['category']}</b>  {spent:,.0f} / {limit:,.0f} {sym}  "
                f"✅ <i>{left:,.0f} left</i>"
            )
    return "\n".join(lines)


def format_sync_status(status: dict[str, Any]) -> str:
    """Format sync status as HTML."""
    s = status.get("status", "unknown")
    if s == "never_synced":
        return "🔄 Sync started. No previous run on record."
    if s == "running":
        started = status.get("started_at", "—")
        return f"🔄 Sync in progress…\nStarted: {started}"
    imported = status.get("tx_imported", 0)
    completed = status.get("completed_at", "—")
    error = status.get("error")
    if s == "error":
        return f"❌ Last sync failed.\nError: {error}\nCompleted: {completed}"
    return (
        f"✅ Sync complete.\n{imported} transactions imported\nCompleted: {completed}"
    )
