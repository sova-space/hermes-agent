"""Salary-cycle month query tests."""

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


def test_close_salary_income_dates_are_one_cycle(session):
    account = _account(session)
    today = date.today()
    previous_salary = today - timedelta(days=35)
    current_salary = today - timedelta(days=5)
    current_topup = today - timedelta(days=2)
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
            monobank_id="salary-current",
            amount=45000,
            currency="UAH",
            date=current_salary,
            description="Salary current",
            category=cat.INCOME,
        ),
        Transaction(
            account_id=account.id,
            monobank_id="salary-current-topup",
            amount=21000,
            currency="UAH",
            date=current_topup,
            description="Salary current topup",
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

    current = queries.get_month_cycle_summary(offset=0)
    previous = queries.get_month_cycle_summary(offset=1)

    assert current["spending"]["period_start"] == current_salary.isoformat()
    assert previous["spending"]["period_start"] == previous_salary.isoformat()
    assert current["has_previous"] is True
    assert current["has_next"] is False


def test_previous_month_balance_is_as_of_selected_month_end(session):
    account = _account(session, balance=57_700)
    today = date.today()
    previous_salary = today - timedelta(days=35)
    current_salary = today - timedelta(days=5)
    previous_end = current_salary - timedelta(days=1)
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
            monobank_id="salary-current",
            amount=45000,
            currency="UAH",
            date=current_salary,
            description="Salary current",
            category=cat.INCOME,
        ),
        Transaction(
            account_id=account.id,
            monobank_id="after-income",
            amount=10_000,
            currency="UAH",
            date=current_salary + timedelta(days=1),
            description="After income",
            category=cat.INCOME,
        ),
        Transaction(
            account_id=account.id,
            monobank_id="after-food",
            amount=-2_700,
            currency="UAH",
            date=today,
            description="After food",
            category=cat.FOOD_AND_DRINK,
        ),
    ])
    session.commit()

    summary = queries.get_month_cycle_summary(offset=1)

    assert summary["spending"]["period_end"] == previous_end.isoformat()
    assert summary["income"]["balances"] == {"UAH": 5_400}
