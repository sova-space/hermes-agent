"""Format Finance API data as Telegram HTML messages."""

from collections import defaultdict
from datetime import UTC, date, datetime
from typing import Any

from finance_api.bot.telegram_fmt import bold, code, italic, pre
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


def _short_name(name: str, currency: str) -> str:
    """Strip 'Monobank ' prefix and trailing currency code from account name."""
    return name.replace("Monobank ", "").replace(f" {currency}", "").strip()


def format_balance(accounts: list[dict[str, Any]]) -> str:
    """Format account balances as a monospace code block grouped by currency."""
    if not accounts:
        return "No accounts synced yet. Run /sync first."

    by_currency: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for a in accounts:
        by_currency[a["currency"]].append(a)

    short: dict[str, str] = {
        a["name"]: _short_name(a["name"], a["currency"]) for a in accounts
    }
    fmt: dict[str, str] = {
        a["name"]: _fmt_amount(round(a["balance"]), a["currency"]) for a in accounts
    }
    group_totals: dict[str, str] = {
        currency: _fmt_amount(round(sum(a["balance"] for a in group)), currency)
        for currency, group in by_currency.items()
        if len(group) > 1
    }

    name_w = max(len(s) for s in short.values())
    amount_w = max(
        max(len(s) for s in fmt.values()),
        max((len(s) for s in group_totals.values()), default=0),
    )
    div = "─" * (name_w + 2 + amount_w)

    pre_lines: list[str] = []
    for i, (currency, group) in enumerate(by_currency.items()):
        if i > 0:
            pre_lines.append("")
        pre_lines.append(currency)
        fops = [a for a in group if a.get("is_fop")]
        cards = [a for a in group if not a.get("is_fop")]
        for a in fops:
            pre_lines.append(
                f"  {short[a['name']]:<{name_w}}  {fmt[a['name']]:>{amount_w}}"
            )
        if fops and cards:
            pre_lines.append("")
        for a in cards:
            pre_lines.append(
                f"  {short[a['name']]:<{name_w}}  {fmt[a['name']]:>{amount_w}}"
            )
        if currency in group_totals:
            pre_lines.append(f"  {div}")
            pre_lines.append(
                f"  {'Total':<{name_w}}  {group_totals[currency]:>{amount_w}}"
            )

    latest_sync = max(
        (a["synced_at"] for a in accounts if a.get("synced_at")),
        default=None,
    )
    return (
        f"{bold('Mono')}\n\n"
        + pre("\n".join(pre_lines))
        + f"\n\n🕐 {_fmt_ago(latest_sync)}"
    )


def format_income_summary(summary: dict[str, Any]) -> str:
    """Format monthly income vs spending as a monospace code block."""
    by_cur = summary.get("by_currency", {})
    if not by_cur:
        return ""

    period = summary.get("period", "")
    LABEL_W = len("Spending")  # longest label — keeps columns stable

    all_amt_strs: list[str] = []
    for c, v in by_cur.items():
        total = v["fop"] + v["personal"]
        for val in (v["fop"], v["personal"], total, v["spending"]):
            if val:
                all_amt_strs.append(_fmt_amount(val, c))
    if not all_amt_strs:
        return ""

    amount_w = max(len(s) for s in all_amt_strs)
    div = "─" * (LABEL_W + 2 + amount_w)

    lines = [f"Income · {period}"]
    for i, (c, v) in enumerate(by_cur.items()):
        if i:
            lines.append("")
        lines.append(c)
        if v["fop"]:
            lines.append(
                f"  {'FOP':<{LABEL_W}}  {_fmt_amount(v['fop'], c):>{amount_w}}"
            )
        if v["personal"]:
            p_amt = _fmt_amount(v["personal"], c)
            lines.append(f"  {'Personal':<{LABEL_W}}  {p_amt:>{amount_w}}")
        total = v["fop"] + v["personal"]
        if v["fop"] and v["personal"]:
            lines.append(f"  {div}")
            lines.append(f"  {'Total':<{LABEL_W}}  {_fmt_amount(total, c):>{amount_w}}")
        if v["spending"]:
            pct = f"  {round(v['spending'] / total * 100)}%" if total else ""
            s_amt = _fmt_amount(v["spending"], c)
            lines.append(f"  {'Spending':<{LABEL_W}}  {s_amt:>{amount_w}}{pct}")

    return pre("\n".join(lines))


def format_stats(spending: dict[str, float], period: str = "this_month") -> str:
    """Format spending breakdown as HTML."""
    if not spending:
        return f"No spending data for {_PERIOD_LABEL.get(period, period)}."
    total = sum(spending.values())
    label = _PERIOD_LABEL.get(period, period)
    lines = [bold(f"📊 Spending — {label}"), ""]
    for category_name, amount in sorted(
        spending.items(), key=lambda x: x[1], reverse=True
    ):
        pct = round(amount / total * 100) if total else 0
        em = _emoji(category_name)
        lines.append(
            f"{em} {bold(category_name)}  {amount:,.0f} ₴  {italic(f'{pct}%')}"
        )
    lines += ["", bold(f"Total: {total:,.0f} ₴")]
    return "\n".join(lines)


def format_budget(budgets: list[dict[str, Any]]) -> str:
    """Format budget limits vs spending as HTML."""
    label = date.today().strftime("%B %Y")
    if not budgets:
        return (
            f"{bold(f'📉 Budget — {label}')}\n\n"
            "No limits set yet.\n"
            f"Use {code('/budget set <category> <amount>')} to add one."
        )
    lines = [bold(f"📉 Budget — {label}"), ""]
    for b in budgets:
        em = _emoji(b["category"])
        spent = b["spent"]
        limit = b["monthly_limit"]
        sym = _sym(b["currency"])
        if b["exceeded"]:
            over = spent - limit
            lines.append(
                f"{em} {bold(b['category'])}  {spent:,.0f} / {limit:,.0f} {sym}  "
                f"⚠️ {italic(f'over by {over:,.0f}')}"
            )
        else:
            left = b["remaining"]
            lines.append(
                f"{em} {bold(b['category'])}  {spent:,.0f} / {limit:,.0f} {sym}  "
                f"✅ {italic(f'{left:,.0f} left')}"
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
