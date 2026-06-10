"""Transaction labeling tests."""

from datetime import date

import pytest
from sqlmodel import select

from finance_api.domains.accounts.models import Account
from finance_api.domains.transactions import categories as cat
from finance_api.domains.transactions.models import Transaction


def test_label_latest_uncategorized_transaction_updates_matching_tx(
    session, monkeypatch
):
    import finance_api.domains.transactions.labeling as labeling

    monkeypatch.setattr(labeling, "engine", session.bind)
    account = Account(
        monobank_id="acc-1",
        name="Card",
        currency="UAH",
        account_type="black",
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    tx = Transaction(
        account_id=account.id,
        monobank_id="monobank_1",
        amount=-420,
        currency="UAH",
        date=date(2026, 6, 10),
        description="SHOCKO CAFE",
        category=None,
    )
    session.add(tx)
    session.commit()

    result = labeling.label_latest_uncategorized("shocko", cat.FOOD_AND_DRINK)

    assert result["description"] == "SHOCKO CAFE"
    assert result["category"] == cat.FOOD_AND_DRINK
    updated = session.exec(select(Transaction)).one()
    assert updated.category == cat.FOOD_AND_DRINK
    assert updated.mode == "solo"


def test_label_latest_uncategorized_rejects_unknown_category(session, monkeypatch):
    import finance_api.domains.transactions.labeling as labeling

    monkeypatch.setattr(labeling, "engine", session.bind)

    with pytest.raises(ValueError, match="Unknown category"):
        labeling.label_latest_uncategorized("x", "Eating Well")
