"""Salary-cycle month query tests."""

from datetime import date, timedelta

from finance_api.domains.accounts.models import Account
from finance_api.domains.insights import queries
from finance_api.domains.transactions import categories as cat
from finance_api.domains.transactions.models import Transaction


def _account(session, *, is_fop=False):
    account = Account(
        monobank_id=f"acc-{is_fop}",
        name="Card",
        currency="UAH",
        account_type="black",
        is_fop=is_fop,
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    return account


def test_current_month_cycle_starts_at_latest_big_income(session):
    account = _account(session)
    today = date.today()
    previous_salary = today - timedelta(days=31)
    current_salary = today - timedelta(days=2)
    session.add_all([
        Transaction(
            account_id=account.id,
            monobank_id="salary-prev",
            amount=40000,
            currency="UAH",
            date=previous_salary,
            description="Salary previous",
            category=cat.INCOME,
        ),
        Transaction(
            account_id=account.id,
            monobank_id="old-food",
            amount=-900,
            currency="UAH",
            date=previous_salary + timedelta(days=3),
            description="Old food",
            category=cat.FOOD_AND_DRINK,
        ),
        Transaction(
            account_id=account.id,
            monobank_id="salary-current",
            amount=45000,
            currency="UAH",
            date=current_salary,
            description="Salary current",
            category=cat.INCOME,
        ),
        Transaction(
            account_id=account.id,
            monobank_id="new-food",
            amount=-300,
            currency="UAH",
            date=today,
            description="New food",
            category=cat.FOOD_AND_DRINK,
        ),
    ])
    session.commit()

    summary = queries.get_month_cycle_summary(offset=0)

    assert summary["spending"]["period_start"] == current_salary.isoformat()
    assert summary["has_previous"] is True
    assert summary["has_next"] is False
    rows = summary["spending"]["rows"]
    assert rows == [
        {"category": cat.FOOD_AND_DRINK, "currency": "UAH", "amount": 300.0}
    ]


def test_previous_month_cycle_ends_before_next_salary(session):
    account = _account(session)
    today = date.today()
    previous_salary = today - timedelta(days=31)
    current_salary = today - timedelta(days=2)
    session.add_all([
        Transaction(
            account_id=account.id,
            monobank_id="salary-prev",
            amount=40000,
            currency="UAH",
            date=previous_salary,
            description="Salary previous",
            category=cat.INCOME,
        ),
        Transaction(
            account_id=account.id,
            monobank_id="old-food",
            amount=-900,
            currency="UAH",
            date=previous_salary + timedelta(days=3),
            description="Old food",
            category=cat.FOOD_AND_DRINK,
        ),
        Transaction(
            account_id=account.id,
            monobank_id="salary-current",
            amount=45000,
            currency="UAH",
            date=current_salary,
            description="Salary current",
            category=cat.INCOME,
        ),
        Transaction(
            account_id=account.id,
            monobank_id="new-food",
            amount=-300,
            currency="UAH",
            date=today,
            description="New food",
            category=cat.FOOD_AND_DRINK,
        ),
    ])
    session.commit()

    summary = queries.get_month_cycle_summary(offset=1)

    assert summary["spending"]["period_start"] == previous_salary.isoformat()
    assert (
        summary["spending"]["period_end"]
        == (current_salary - timedelta(days=1)).isoformat()
    )
    assert summary["has_next"] is True
    rows = summary["spending"]["rows"]
    assert rows == [
        {"category": cat.FOOD_AND_DRINK, "currency": "UAH", "amount": 900.0}
    ]
