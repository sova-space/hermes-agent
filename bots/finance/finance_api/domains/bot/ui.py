"""Reusable Telegram UI payloads for finance views.

The standalone finance bot and Hermes' /finance command need the same one-message
inline UI. Keep the view rendering here and expose it over HTTP so Hermes does
not duplicate finance formatting logic.
"""

from typing import Any

from finance_api.domains.bot.formatter import (
    CATEGORY_EMOJI,
    format_balance,
    format_income_summary,
    format_month_report,
    format_spending_category,
    format_spending_summary,
    format_subscriptions,
    format_sync_status,
)
from finance_api.domains.bot.handlers import (
    BALANCE_CALLBACK,
    INCOME_CALLBACK,
    MONTH_CALLBACK,
    SPENDING_CALLBACK,
    SPENDING_CAT_PREFIX,
    SUBS_CALLBACK,
    SYNC_CALLBACK,
)
from finance_api.domains.insights.queries import (
    get_account_balances,
    get_hidden_account_balances,
    get_income_summary,
    get_month_cycle_summary,
    get_spending_summary,
    get_subscriptions,
    get_sync_health,
)
from finance_api.domains.transactions.categories import CASHBACK, COUPLE_TRANSFER

PARSE_MODE = "HTML"


def _button(
    text: str, callback_data: str | None = None, url: str | None = None
) -> dict[str, str]:
    payload = {"text": text}
    if callback_data is not None:
        payload["callback_data"] = callback_data
    if url is not None:
        payload["url"] = url
    return payload


def balance_keyboard() -> dict[str, list[list[dict[str, str]]]]:
    """Main finance inline keyboard as raw Telegram Bot API JSON."""
    return {
        "inline_keyboard": [
            [
                _button("💳 Balance", callback_data=BALANCE_CALLBACK),
                _button("📅 Month", callback_data=MONTH_CALLBACK),
            ],
            [
                _button("📊 Spending", callback_data=SPENDING_CALLBACK),
                _button("💰 Income", callback_data=INCOME_CALLBACK),
            ],
            [
                _button("🔁 Subs", callback_data=SUBS_CALLBACK),
                _button("🔄 Sync", callback_data=SYNC_CALLBACK),
            ],
        ]
    }


_CAT_SHORT: dict[str, str] = {
    "Food & Drink": "Food",
    "Groceries": "Groceries",
    "Transportation": "Transport",
    "Healthcare": "Health",
    "Shopping": "Shopping",
    "Entertainment": "Fun",
    "Travel": "Travel",
    "Subscriptions": "Subs",
    "Utilities": "Utils",
    "ATM & Cash": "Cash",
    "Finance": "Finance",
    "Education": "Education",
    "Pets": "Pets",
    "Partner": "Partner",
}


def spending_keyboard(data: dict[str, Any]) -> dict[str, list[list[dict[str, str]]]]:
    """Category drill-down buttons + back button as raw Telegram JSON."""
    rows_data = [
        r
        for r in data.get("rows", [])
        if r["currency"] == "UAH" and r["category"] not in {COUPLE_TRANSFER, CASHBACK}
    ]
    rows_data.sort(key=lambda r: r["amount"], reverse=True)
    buttons = []
    for r in rows_data:
        category = r["category"]
        label = (
            f"{CATEGORY_EMOJI.get(category, '📦')} {_CAT_SHORT.get(category, category)}"
        )
        buttons.append(_button(label, callback_data=f"{SPENDING_CAT_PREFIX}{category}"))
    rows = [buttons[i : i + 3] for i in range(0, len(buttons), 3)]
    rows.append([_button("← Back", callback_data=BALANCE_CALLBACK)])
    return {"inline_keyboard": rows}


def back_to_spending_keyboard() -> dict[str, list[list[dict[str, str]]]]:
    """Back button from a category detail view to the spending summary."""
    return {
        "inline_keyboard": [[_button("← Spending", callback_data=SPENDING_CALLBACK)]]
    }


def month_keyboard(summary: dict[str, Any]) -> dict[str, list[list[dict[str, str]]]]:
    """Month navigation buttons + main menu back button."""
    offset = int(summary.get("offset", 0))
    rows: list[list[dict[str, str]]] = []
    month_row: list[dict[str, str]] = []
    if summary.get("has_previous"):
        month_row.append(_button("← Prev", callback_data=f"month:{offset + 1}"))
    if summary.get("has_next"):
        month_row.append(_button("Next →", callback_data=f"month:{offset - 1}"))
    if month_row:
        rows.append(month_row)
    year_row: list[dict[str, str]] = []
    if summary.get("has_previous"):
        year_row.append(_button("← Year", callback_data=f"month:{offset + 12}"))
    if offset >= 12:
        year_row.append(_button("Year →", callback_data=f"month:{offset - 12}"))
    if year_row:
        rows.append(year_row)
    rows.append([_button("← Back", callback_data=BALANCE_CALLBACK)])
    return {"inline_keyboard": rows}


def view_payload(view: str = "balance", category: str | None = None) -> dict[str, Any]:
    """Return a Telegram-ready UI payload for one finance view."""
    if view == "balance":
        accounts = get_account_balances()
        return {
            "text": format_balance(accounts),
            "parse_mode": PARSE_MODE,
            "reply_markup": balance_keyboard(),
        }

    if view == "skipped":
        accounts = get_hidden_account_balances()
        text = format_balance(accounts) if accounts else "No skipped accounts."
        return {
            "text": text,
            "parse_mode": PARSE_MODE,
            "reply_markup": balance_keyboard(),
        }

    if view == "income":
        text = (
            format_income_summary(get_income_summary())
            or "No income data for this month yet."
        )
        return {
            "text": text,
            "parse_mode": PARSE_MODE,
            "reply_markup": balance_keyboard(),
        }

    if view == "month":
        summary = get_month_cycle_summary()
        return {
            "text": format_month_report(summary["income"], summary["spending"]),
            "parse_mode": PARSE_MODE,
            "reply_markup": month_keyboard(summary),
        }

    if view.startswith("month:"):
        summary = get_month_cycle_summary(int(view.split(":", 1)[1]))
        return {
            "text": format_month_report(summary["income"], summary["spending"]),
            "parse_mode": PARSE_MODE,
            "reply_markup": month_keyboard(summary),
        }

    if view == "spending":
        data = get_spending_summary()
        text = format_spending_summary(data) or "No spending recorded yet this cycle."
        return {
            "text": text,
            "parse_mode": PARSE_MODE,
            "reply_markup": spending_keyboard(data),
        }

    if view == "spending_category" and category:
        data = get_spending_summary()
        return {
            "text": format_spending_category(data, category),
            "parse_mode": PARSE_MODE,
            "reply_markup": back_to_spending_keyboard(),
        }

    if view == "subs":
        return {
            "text": format_subscriptions(get_subscriptions()),
            "parse_mode": PARSE_MODE,
            "reply_markup": balance_keyboard(),
        }

    if view == "sync_status":
        return {
            "text": format_sync_status(get_sync_health()),
            "parse_mode": PARSE_MODE,
            "reply_markup": balance_keyboard(),
        }

    return {
        "text": "Unknown finance view.",
        "parse_mode": PARSE_MODE,
        "reply_markup": balance_keyboard(),
    }
