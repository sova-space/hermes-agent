"""Assistant tool wiring tests."""

import json
from datetime import date

import pytest

from finance_api.domains.assistant import loop


@pytest.mark.asyncio
async def test_record_income_tool_calls_manual_recorder(monkeypatch):
    calls = []

    def fake_record_manual_income(**kwargs):
        calls.append(kwargs)
        return {"ok": True, "amount": kwargs["amount"]}

    monkeypatch.setattr(loop, "record_manual_income", fake_record_manual_income)

    result = await loop._dispatch_tool(
        "record_income",
        {
            "amount": 2500,
            "currency": "usd",
            "description": "Cash consulting",
            "date": "2026-06-10",
            "notes": "from chat",
        },
    )

    assert json.loads(result) == {"ok": True, "amount": 2500}
    assert calls == [
        {
            "amount": 2500,
            "currency": "usd",
            "description": "Cash consulting",
            "received_on": date(2026, 6, 10),
            "notes": "from chat",
        }
    ]


def test_record_income_tool_is_exposed_to_openrouter():
    names = [tool["function"]["name"] for tool in loop._OPENAI_TOOLS]
    assert "record_income" in names
    assert "label_uncategorized" in names
