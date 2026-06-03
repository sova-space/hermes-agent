"""Format Finance API data as Telegram HTML messages."""

from collections import defaultdict
from datetime import UTC, date, datetime
from typing import Any

from finance_api.bot.telegram_fmt import bold, code, expandable_blockquote, italic
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


_CURRENCY_FLAG: dict[str, str] = {
    "UAH": "🇺🇦",
    "USD": "🇺🇸",
    "EUR": "🇪🇺",
    "GBP": "🇬🇧",
}


def format_balance(accounts: list[dict[str, Any]]) -> str:
    """Format balances: currency totals visible, per-account details expandable."""
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
    group_totals: dict[str, float] = {
        currency: round(sum(a["balance"] for a in group))
        for currency, group in by_currency.items()
    }

    # Totals section — always visible
    total_lines: list[str] = []
    for currency, _group in by_currency.items():
        flag = _CURRENCY_FLAG.get(currency, "💱")
        total_str = _fmt_amount(group_totals[currency], currency)
        total_lines.append(f"{flag} {currency}  {bold(total_str)}")

    # Breakdown section — collapsed by default
    name_w = max(len(s) for s in short.values())
    amount_w = max(len(s) for s in fmt.values())
    breakdown_lines: list[str] = [bold("Breakdown")]
    for i, (_currency, group) in enumerate(by_currency.items()):
        if i > 0:
            breakdown_lines.append("")
        fops = [a for a in group if a.get("is_fop")]
        cards = [a for a in group if not a.get("is_fop")]
        for a in fops + cards:
            breakdown_lines.append(
                f"{short[a['name']]:<{name_w}}  {fmt[a['name']]:>{amount_w}}"
            )

    latest_sync = max(
        (a["synced_at"] for a in accounts if a.get("synced_at")),
        default=None,
    )
    return (
        f"💳 {bold('Mono')}\n\n"
        + "\n".join(total_lines)
        + "\n\n"
        + expandable_blockquote("\n".join(breakdown_lines))
        + f"\n\n🕐 {_fmt_ago(latest_sync)}"
    )


def _fmt_income_period(summary: dict[str, Any]) -> str:
    start_raw = summary.get("period_start")
    end_raw = summary.get("period_end")
    if not start_raw or not end_raw:
        return summary.get("period", "")
    start = date.fromisoformat(start_raw)
    end = date.fromisoformat(end_raw)
    if start.month == end.month:
        return f"{start.strftime('%b %-d')} - {end.strftime('%-d')}"
    return f"{start.strftime('%b %-d')} - {end.strftime('%b %-d')}"


def format_income_summary(summary: dict[str, Any]) -> str:
    """Format income: earned totals visible, source/spending details expandable."""
    by_cur = summary.get("by_currency", {})
    if not by_cur:
        return ""

    period = _fmt_income_period(summary)

    # Validate there's something to show
    has_data = any(v["fop"] or v["personal"] for v in by_cur.values())
    if not has_data:
        return ""

    # Collect all salary transactions and all spending, grouped by currency
    all_txns: list[tuple[str, str, dict[str, Any]]] = []
    for currency, v in by_cur.items():
        for t in v.get("fop_txns", []):
            all_txns.append(("FOP", currency, t))
        for t in v.get("personal_txns", []):
            all_txns.append(("Personal", currency, t))
    all_txns.sort(key=lambda x: x[2]["date"])

    if not all_txns:
        return ""

    received_lines: list[str] = []
    for source, currency, t in all_txns:
        dt = date.fromisoformat(t["date"])
        sender = t["description"].removeprefix("Від: ").strip()
        flag = _CURRENCY_FLAG.get(currency, "💱")
        label = f"{flag} {source} · {dt.strftime('%b %-d')} · {sender}"
        amt = bold(_fmt_amount(t["amount"], currency))
        received_lines.append(f"  {label}  {amt}")

    # Current balance per currency from personal accounts
    balances = summary.get("balances", {})
    balance_lines: list[str] = []
    for currency, bal in sorted(balances.items()):
        if bal == 0:
            continue
        flag = _CURRENCY_FLAG.get(currency, "💱")
        balance_lines.append(f"  {flag} {bold(_fmt_amount(bal, currency))}")

    body = f"💵 {bold('Received')}\n" + "\n".join(received_lines)
    if balance_lines:
        body += f"\n\n💳 {bold('Balance now')}\n" + "\n".join(balance_lines)

    return f"💰 {bold(f'Income · {period}')}\n\n" + body


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
