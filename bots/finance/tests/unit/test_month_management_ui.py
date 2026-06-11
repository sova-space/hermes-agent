"""Month management UI tests."""

from finance_api.domains.bot import formatter, ui


def test_balance_keyboard_has_month_management_button():
    keyboard = ui.balance_keyboard()["inline_keyboard"]

    assert any(
        button.get("callback_data") == "month" for row in keyboard for button in row
    )


def test_month_report_formats_income_and_spending_html():
    text = formatter.format_month_report(
        income={
            "period_start": "2026-06-01",
            "by_currency": {
                "UAH": {
                    "fop": 0,
                    "personal": 40000,
                    "fop_txns": [],
                    "personal_txns": [
                        {
                            "date": "2026-06-01",
                            "amount": 40000,
                            "description": "Salary",
                        }
                    ],
                }
            },
            "balances": {"UAH": 10000},
        },
        spending={
            "period_start": "2026-06-01",
            "period_end": "2026-06-11",
            "rows": [
                {"category": "Food & Drink", "currency": "UAH", "amount": 2500},
            ],
            "details": {},
        },
    )

    assert "<b>Month" in text
    assert "Income" in text
    assert "Spending" in text
    assert "Food & Drink" in text
