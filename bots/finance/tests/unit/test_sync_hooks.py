"""New transaction notification tests."""

from finance_api.domains.transactions import categories as cat


def test_format_new_transaction_message_for_known_food_is_short_and_playful():
    from finance_api.domains.sync.hooks import format_new_transaction_message

    text = format_new_transaction_message({
        "description": "SHOCKO CAFE",
        "amount": -420,
        "currency": "UAH",
        "category": cat.FOOD_AND_DRINK,
    })

    assert "SHOCKO CAFE" in text
    assert "420" in text
    assert "ate well" in text
    assert "What category" not in text


def test_format_new_transaction_message_for_uncategorized_asks_question():
    from finance_api.domains.sync.hooks import format_new_transaction_message

    text = format_new_transaction_message({
        "description": "UNKNOWN SHOP",
        "amount": -100,
        "currency": "UAH",
        "category": None,
    })

    assert "UNKNOWN SHOP" in text
    assert "What category is this" in text
    assert "Food & Drink" in text
