"""OpenRouter-backed conversational agent for free-form money questions.

Mirrors the tool-calling loop pattern in `doer_api/agent/loop.py`, scoped to
read-only Finance API queries instead of GitHub operations.
"""

import asyncio
import json

import anthropic
import structlog

from finance_api.core.config import settings
from finance_api.domains.budgets.queries import list_budgets_vs_spending
from finance_api.domains.insights.queries import (
    get_account_balances,
    get_income_summary,
    get_monthly_trend,
    get_recent_transactions,
    get_spending_by_category,
    get_subscriptions,
    get_sync_health,
)

log = structlog.get_logger(__name__)

_MAX_TOOL_TURNS = 8  # safety cap on tool-calling round-trips per message
_MAX_HISTORY = 20  # trimmed message count kept per chat

_client = anthropic.AsyncAnthropic(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.openrouter_api_key,
)

_sessions: dict[int, list[dict]] = {}

_TOOL_DEFS: list[dict] = [
    {
        "name": "get_balances",
        "description": "Current balances for all visible accounts.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_spending",
        "description": "Spending grouped by category for a period.",
        "input_schema": {
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "description": (
                        "this_month, last_month, last_7d, last_30d, or last_90d"
                    ),
                },
            },
        },
    },
    {
        "name": "get_monthly_trend",
        "description": "Month-by-month income vs. expenses.",
        "input_schema": {
            "type": "object",
            "properties": {
                "months": {"type": "integer", "description": "Defaults to 3."},
            },
        },
    },
    {
        "name": "get_recent_transactions",
        "description": "Most recent transactions, optionally filtered by period.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Defaults to 20."},
                "period": {
                    "type": "string",
                    "description": "this_month, last_month, last_7d, etc.",
                },
            },
        },
    },
    {
        "name": "get_budgets",
        "description": "Budget limits vs. actual spending this month.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_subscriptions",
        "description": "Detected recurring subscriptions.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_income_summary",
        "description": "Income summary for the current period.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_sync_status",
        "description": "When the bank data was last synced, and its outcome.",
        "input_schema": {"type": "object", "properties": {}},
    },
]

_SYSTEM = (
    "You are Nazar's personal finance assistant, built into @sova_finance_bot. "
    "Answer conversational questions about his Monobank accounts, spending, "
    "budgets, income, and subscriptions using the tools provided — never guess "
    "at numbers.\n\n"
    "Rules:\n"
    "- Always call get_balances first before answering any money question, so "
    "you have current context. If accounts come back empty, tell Nazar to tap "
    "the 🔄 Sync button.\n"
    "- Keep answers short and conversational — a sentence or two, not a report.\n"
    "- Use these category emojis when listing spending: 🛒 Groceries, "
    "🍔 Restaurants, 🚇 Transport, 🏠 Housing, 💊 Health, 👗 Clothes, "
    "🛍️ Shopping, 🎮 Entertainment, ✈️ Travel, 💳 Financial, 💸 Transfers, "
    "💰 Income, 📦 Other.\n"
    "- Mind currencies — never sum or compare amounts across different currencies.\n"
    "- This is a Telegram chat: plain text only, no markdown headers or tables."
)


async def _dispatch_tool(name: str, tool_input: dict) -> str:
    """Run the named read-only query and return a JSON string result."""
    try:
        if name == "get_balances":
            result = await asyncio.to_thread(get_account_balances)
        elif name == "get_spending":
            result = await asyncio.to_thread(
                get_spending_by_category,
                period=tool_input.get("period", "this_month"),
            )
        elif name == "get_monthly_trend":
            result = await asyncio.to_thread(
                get_monthly_trend, months=tool_input.get("months", 3)
            )
        elif name == "get_recent_transactions":
            result = await asyncio.to_thread(
                get_recent_transactions,
                limit=tool_input.get("limit", 20),
                period=tool_input.get("period"),
            )
        elif name == "get_budgets":
            items = await asyncio.to_thread(list_budgets_vs_spending)
            result = [item.model_dump() for item in items]
        elif name == "get_subscriptions":
            result = await asyncio.to_thread(get_subscriptions)
        elif name == "get_income_summary":
            result = await asyncio.to_thread(get_income_summary)
        elif name == "get_sync_status":
            result = await asyncio.to_thread(get_sync_health)
        else:
            return f"Unknown tool: {name}"
    except Exception as exc:
        log.warning("assistant_tool_error", tool=name, error=str(exc))
        return f"Error: {exc}"
    return json.dumps(result, default=str)


async def answer(chat_id: int, text: str) -> str:
    """Run one conversational turn for `chat_id` and return the reply text.

    Keeps a short rolling history per chat (in-memory; resets on redeploy) so
    follow-up questions retain context.
    """
    messages = _sessions.setdefault(chat_id, [])
    messages.append({"role": "user", "content": text})

    reply = "Sorry, I couldn't come up with an answer."
    for _ in range(_MAX_TOOL_TURNS):
        response = await _client.messages.create(
            model=settings.finance_assistant_model,
            max_tokens=1024,
            system=_SYSTEM,
            tools=_TOOL_DEFS,  # type: ignore[arg-type]
            messages=messages,  # type: ignore[arg-type]
        )

        text_blocks = [b.text for b in response.content if b.type == "text"]
        if text_blocks:
            reply = "\n".join(text_blocks)

        messages.append(
            {"role": "assistant", "content": response.content}  # type: ignore[arg-type]
        )

        tool_calls = [b for b in response.content if b.type == "tool_use"]
        if response.stop_reason != "tool_use" or not tool_calls:
            break

        tool_results = []
        for block in tool_calls:
            result = await _dispatch_tool(block.name, block.input)  # type: ignore[arg-type]
            log.info("assistant_tool_called", tool=block.name)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result,
            })
        messages.append({"role": "user", "content": tool_results})

    del messages[:-_MAX_HISTORY]
    return reply
