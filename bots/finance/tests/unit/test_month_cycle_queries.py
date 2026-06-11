"""Calendar month query tests."""

from datetime import date, timedelta

from finance_api.domains.accounts.models import Account
from finance_api.domains.insights import queries
from finance_api.domains.transactions import categories as cat
from finance_api.domains.transactions.models import Transaction


def _account(session, *, is_fop=False, balance=0):
    account = Account(
        monobank_id=f"acc-{is_fop}-{balance}",
        name="Card",
        currency="UAH",
        account_type="black",
        is_fop=is_fop,
        balance=balance,
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    return account


def test_current_month_uses_calendar_month_from_first_day(session):
    account = _account(session)
    today = date.today()
    current_start = today.replace(day=1)
    previous_month_day = current_start - timedelta(days=1)
    session.add_all([
        Transaction(
            account_id=account.id,
            monobank_id="old-food",
            amount=-900,
            currency="UAH",
            date=previous_month_day,
            description="Old food",
            category=cat.FOOD_AND_DRINK,
        ),
        Transaction(
            account_id=account.id,
            monobank_id="new-food",
            amount=-300,
            currency="UAH",
            date=current_start,
            description="New food",
            category=cat.FOOD_AND_DRINK,
        ),
    ])
    session.commit()

    summary = queries.get_month_cycle_summary(offset=0)

    assert summary["spending"]["period_start"] == current_start.isoformat()
    assert summary["has_previous"] is True
    assert summary["has_next"] is False
    assert summary["spending"]["rows"] == [
        {"category": cat.FOOD_AND_DRINK, "currency": "UAH", "amount": 300.0}
    ]


def test_previous_month_uses_calendar_month_start_and_end(session):
    account = _account(session)
    today = date.today()
    current_start = today.replace(day=1)
    previous_end = current_start - timedelta(days=1)
    previous_start = previous_end.replace(day=1)
    session.add_all([
        Transaction(
            account_id=account.id,
            monobank_id="old-food",
            amount=-900,
            currency="UAH",
            date=previous_start,
            description="Old food",
            category=cat.FOOD_AND_DRINK,
        ),
        Transaction(
            account_id=account.id,
            monobank_id="new-food",
            amount=-300,
            currency="UAH",
            date=current_start,
            description="New food",
            category=cat.FOOD_AND_DRINK,
        ),
    ])
    session.commit()

    summary = queries.get_month_cycle_summary(offset=1)

    assert summary["spending"]["period_start"] == previous_start.isoformat()
    assert summary["spending"]["period_end"] == previous_end.isoformat()
    assert summary["has_next"] is True
    assert summary["spending"]["rows"] == [
        {"category": cat.FOOD_AND_DRINK, "currency": "UAH", "amount": 900.0}
    ]


def test_previous_month_balance_is_as_of_selected_calendar_month_end(session):
    account = _account(session, balance=57_700)
    today = date.today()
    current_start = today.replace(day=1)
    previous_end = current_start - timedelta(days=1)
    previous_start = previous_end.replace(day=1)
    session.add_all([
        Transaction(
            account_id=account.id,
            monobank_id="salary-prev",
            amount=40_000,
            currency="UAH",
            date=previous_start,
            description="Salary previous",
            category=cat.INCOME,
        ),
        Transaction(
            account_id=account.id,
            monobank_id="after-income",
            amount=10_000,
            currency="UAH",
            date=current_start,
            description="After income",
            category=cat.INCOME,
        ),
        Transaction(
            account_id=account.id,
            monobank_id="after-food",
            amount=-2_700,
            currency="UAH",
            date=current_start,
            description="After food",
            category=cat.FOOD_AND_DRINK,
        ),
    ])
    session.commit()

    summary = queries.get_month_cycle_summary(offset=1)

    assert summary["spending"]["period_end"] == previous_end.isoformat()
    assert summary["income"]["balances"] == {"UAH": 50_400}
