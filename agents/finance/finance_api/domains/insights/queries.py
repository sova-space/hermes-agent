"""Analytics queries over transactions and accounts."""

from datetime import date, timedelta
from typing import Any
from uuid import UUID

from sqlmodel import Session, func, or_, select

from finance_api.core.db.engine import engine
from finance_api.domains.accounts.models import Account
from finance_api.domains.insights.periods import (
    LAST_7D,
    LAST_30D,
    LAST_90D,
    LAST_MONTH,
    SALARY_ANCHORED,
    THIS_MONTH,
)
from finance_api.domains.rules.queries import get_rules, match_label, matches_any
from finance_api.domains.sync.models import SyncRun
from finance_api.domains.transactions import categories as cat
from finance_api.domains.transactions.models import Transaction


def _period_dates(period: str) -> tuple[date, date]:
    today = date.today()
    if period == THIS_MONTH:
        return today.replace(day=1), today
    if period == LAST_MONTH:
        first_this = today.replace(day=1)
        last_prev = first_this - timedelta(days=1)
        return last_prev.replace(day=1), last_prev
    if period == LAST_7D:
        return today - timedelta(days=7), today
    if period == LAST_30D:
        return today - timedelta(days=30), today
    if period == LAST_90D:
        return today - timedelta(days=90), today
    return today.replace(day=1), today


def _month_range(year: int, month: int) -> tuple[date, date]:
    first = date(year, month, 1)
    if month == 12:
        last = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last = date(year, month + 1, 1) - timedelta(days=1)
    return first, last


def _months_ago(n: int) -> tuple[int, int]:
    """Return (year, month) for n months before the current month."""
    today = date.today()
    month = today.month - n
    year = today.year
    while month <= 0:
        month += 12
        year -= 1
    return year, month


def _salary_anchored_start(calendar_start: date, session: Session) -> date:
    """Return earliest FOP income date in the calendar month, or calendar_start."""
    fop_ids = session.exec(select(Account.id).where(Account.is_fop == True)).all()  # noqa: E712
    if not fop_ids:
        return calendar_start
    if calendar_start.month == 12:
        month_end = date(calendar_start.year + 1, 1, 1) - timedelta(days=1)
    else:
        month_end = date(calendar_start.year, calendar_start.month + 1, 1) - timedelta(
            days=1
        )
    first = session.exec(
        select(func.min(Transaction.date))
        .where(Transaction.account_id.in_(fop_ids))
        .where(Transaction.amount > 0)
        .where(Transaction.date >= calendar_start)
        .where(Transaction.date <= month_end)
    ).first()
    return first or calendar_start


def get_account_balances() -> list[dict[str, Any]]:
    """Return current balances for all visible (non-hidden) synced accounts."""
    with Session(engine) as session:
        accounts = session.exec(
            select(Account).where(Account.hidden == False)  # noqa: E712
        ).all()
        return [
            {
                "account_id": str(a.id),
                "name": a.name,
                "currency": a.currency,
                "balance": a.balance,
                "type": a.account_type,
                "is_fop": a.is_fop,
                "synced_at": a.synced_at.isoformat() if a.synced_at else None,
            }
            for a in accounts
        ]


def get_hidden_account_balances() -> list[dict[str, Any]]:
    """Return balances for hidden (skipped) accounts."""
    with Session(engine) as session:
        accounts = session.exec(
            select(Account).where(Account.hidden == True)  # noqa: E712
        ).all()
        return [
            {
                "account_id": str(a.id),
                "name": a.name,
                "currency": a.currency,
                "balance": a.balance,
                "type": a.account_type,
                "is_fop": a.is_fop,
                "synced_at": a.synced_at.isoformat() if a.synced_at else None,
            }
            for a in accounts
        ]


def get_visible_account_count() -> int:
    """Return the number of visible accounts — used for sync time estimation."""
    with Session(engine) as session:
        return session.exec(
            select(func.count(Account.id)).where(Account.hidden == False)  # noqa: E712
        ).one()


def get_spending_by_category(
    period: str = "this_month",
    account_id: UUID | None = None,
    mode: str | None = None,
    exclude_uncategorized: bool = False,
    start: date | None = None,
    end: date | None = None,
) -> list[dict[str, Any]]:
    """Return total spending grouped by category and currency for the given period.

    When ``start`` and ``end`` are both provided they override ``period`` so that
    arbitrary date ranges (e.g. trip date ranges) can be queried without defining
    a named period.

    Returns a list of dicts with keys: ``category``, ``currency``, ``amount``.
    Amounts are positive (expenses are negated).
    """
    use_explicit_range = start is not None and end is not None
    if not use_explicit_range:
        start, end = _period_dates(period)
    with Session(engine) as session:
        if not use_explicit_range and period in SALARY_ANCHORED:
            start = _salary_anchored_start(start, session)
        q = (
            select(
                Transaction.category,
                Transaction.currency,
                func.sum(Transaction.amount),
            )
            .where(Transaction.date >= start)
            .where(Transaction.date <= end)
            .where(Transaction.amount < 0)
            .where(Transaction.is_pending == False)  # noqa: E712
        )
        if account_id:
            q = q.where(Transaction.account_id == account_id)
        if mode is not None:
            q = q.where(Transaction.mode == mode)
        if exclude_uncategorized:
            q = q.where(Transaction.category.is_not(None))  # type: ignore[union-attr]
        q = q.group_by(Transaction.category, Transaction.currency)
        rows = session.exec(q).all()
        return [
            {
                "category": category or "Uncategorized",
                "currency": currency,
                "amount": round(abs(total), 2),
            }
            for category, currency, total in rows
        ]


def get_monthly_trend(
    months: int = 3,
    account_id: UUID | None = None,
    mode: str | None = None,
) -> list[dict[str, Any]]:
    """Return month-by-month income and expense totals, split by currency.

    Returns a list of dicts with keys: ``month``, ``currency``, ``income``,
    ``expenses``.  Each (month, currency) pair is a separate row so that
    multi-currency amounts are never summed across currencies.
    """
    result = []
    for i in range(months - 1, -1, -1):
        year, month = _months_ago(i)
        first, last = _month_range(year, month)

        def _sums_by_currency(
            session: Session,
            start: date,
            end: date,
            condition: Any,
        ) -> dict[str, float]:
            base = (
                select(Transaction.currency, func.sum(Transaction.amount))
                .where(Transaction.date >= start)
                .where(Transaction.date <= end)
                .where(Transaction.is_pending == False)  # noqa: E712
                .where(condition)
                .group_by(Transaction.currency)
            )
            if account_id:
                base = base.where(Transaction.account_id == account_id)
            if mode is not None:
                base = base.where(Transaction.mode == mode)
            return {currency: total for currency, total in session.exec(base).all()}

        with Session(engine) as session:
            anchored_first = _salary_anchored_start(first, session) if i == 0 else first
            income_by_cur = _sums_by_currency(
                session, anchored_first, last, Transaction.amount > 0
            )
            expenses_by_cur = _sums_by_currency(
                session, anchored_first, last, Transaction.amount < 0
            )

        all_currencies = set(income_by_cur) | set(expenses_by_cur)
        month_label = first.strftime("%b %Y")
        for currency in sorted(all_currencies):
            result.append({
                "month": month_label,
                "currency": currency,
                "income": round(income_by_cur.get(currency, 0.0), 2),
                "expenses": round(abs(expenses_by_cur.get(currency, 0.0)), 2),
            })
    return result


def get_recent_transactions(
    limit: int = 20,
    period: str | None = None,
    account_id: UUID | None = None,
    mode: str | None = None,
) -> list[dict[str, Any]]:
    """Return recent transactions, optionally filtered by period, account, and mode."""
    with Session(engine) as session:
        q = (
            select(Transaction)
            .order_by(Transaction.date.desc(), Transaction.created_at.desc())  # type: ignore[attr-defined]
            .limit(limit)
        )
        if period:
            start, end = _period_dates(period)
            if period in SALARY_ANCHORED:
                start = _salary_anchored_start(start, session)
            q = q.where(Transaction.date >= start).where(Transaction.date <= end)
        if account_id:
            q = q.where(Transaction.account_id == account_id)
        if mode is not None:
            q = q.where(Transaction.mode == mode)
        txs = session.exec(q).all()
        return [
            {
                "date": t.date.isoformat(),
                "description": t.description,
                "amount": t.amount,
                "currency": t.currency,
                "category": t.category,
                "mode": t.mode,
                "is_pending": t.is_pending,
            }
            for t in txs
        ]


def get_sync_health() -> dict[str, Any]:
    """Return the status of the most recent sync run."""
    with Session(engine) as session:
        last_run = session.exec(
            select(SyncRun).order_by(SyncRun.started_at.desc()).limit(1)  # type: ignore[attr-defined]
        ).first()
        if not last_run:
            return {"status": "never_synced"}
        return {
            "status": last_run.status,
            "started_at": (
                last_run.started_at.isoformat() if last_run.started_at else None
            ),
            "completed_at": (
                last_run.completed_at.isoformat() if last_run.completed_at else None
            ),
            "tx_imported": last_run.tx_imported,
            "error": last_run.error,
        }


def get_spending_summary() -> dict[str, Any]:
    """Return UAH spending by category with per-category transaction details."""
    start, end = _period_dates(THIS_MONTH)
    with Session(engine) as session:
        anchored = _salary_anchored_start(start, session)
        if anchored == start:
            start, end = _period_dates(LAST_MONTH)
            anchored = _salary_anchored_start(start, session)
        rows = get_spending_by_category(start=anchored, end=end)

        # Per-category transaction details for drill-down
        detail_rows = session.exec(
            select(
                Transaction.category,
                Transaction.description,
                Transaction.amount,
                Transaction.date,
            )
            .where(
                Transaction.account_id.in_(
                    select(Account.id).where(Account.is_fop == False)  # noqa: E712
                )
            )
            .where(Transaction.amount < 0)
            .where(Transaction.date >= anchored)
            .where(Transaction.date <= end)
            .where(Transaction.is_pending == False)  # noqa: E712
            .where(Transaction.category.isnot(None))  # type: ignore[union-attr]
            .where(
                Transaction.category.notin_(  # type: ignore[union-attr]
                    ["Couple Transfer", "Cashback"]
                )
            )
            .where(Transaction.currency == "UAH")
            .order_by(Transaction.category, Transaction.amount)
        ).all()

        by_cat: dict[str, list[dict[str, Any]]] = {}
        for cat_name, desc, amt, dt in detail_rows:
            by_cat.setdefault(cat_name, []).append({
                "description": desc,
                "amount": round(abs(amt), 2),
                "date": dt.isoformat(),
            })

    return {
        "rows": rows,
        "period_start": anchored.isoformat(),
        "period_end": end.isoformat(),
        "details": by_cat,
    }


def get_income_summary() -> dict[str, Any]:
    """Return most recent salary cycle: income by source and spending."""
    start, end = _period_dates(THIS_MONTH)
    with Session(engine) as session:
        anchored = _salary_anchored_start(start, session)
        # If no salary found yet this calendar month, use last month instead.
        if anchored == start:
            start, end = _period_dates(LAST_MONTH)
        # start/end now cover the right calendar month; salary start computed below.

        # FOP USD: external salary only. FOP UAH: internal transfers.
        fop_usd_ids = session.exec(
            select(Account.id).where(
                Account.is_fop == True,  # noqa: E712
                Account.currency == "USD",
            )
        ).all()
        personal_ids = session.exec(
            select(Account.id).where(Account.is_fop == False)  # noqa: E712
        ).all()

        not_cashback = or_(
            Transaction.category.is_(None),
            Transaction.category != cat.CASHBACK,
        )

        def _fop_income_txns(acc_ids: list) -> list[dict[str, Any]]:
            if not acc_ids:
                return []
            rows = session.exec(
                select(Transaction)
                .where(Transaction.account_id.in_(acc_ids))
                .where(Transaction.amount > 0)
                .where(not_cashback)
                .where(Transaction.date >= start)
                .where(Transaction.date <= end)
                .where(Transaction.is_pending == False)  # noqa: E712
                .order_by(Transaction.date)
            ).all()
            return [
                {
                    "date": t.date.isoformat(),
                    "amount": t.amount,
                    "currency": t.currency,
                    "description": t.description,
                }
                for t in rows
            ]

        def _personal_income_txns(acc_ids: list) -> list[dict[str, Any]]:
            if not acc_ids:
                return []
            income_rules = get_rules("personal_income")
            if not income_rules:
                return []
            income_patterns = [p for p, _ in income_rules]
            rows = session.exec(
                select(Transaction)
                .where(Transaction.account_id.in_(acc_ids))
                .where(Transaction.amount > 0)
                .where(not_cashback)
                .where(Transaction.date >= start)
                .where(Transaction.date <= end)
                .where(Transaction.is_pending == False)  # noqa: E712
                .order_by(Transaction.date)
            ).all()
            return [
                {
                    "date": t.date.isoformat(),
                    "amount": t.amount,
                    "currency": t.currency,
                    "description": match_label(t.description, income_rules)
                    or t.description,
                }
                for t in rows
                if matches_any(t.description, income_patterns)
            ]

        fop_txns = _fop_income_txns(fop_usd_ids)
        personal_txns = _personal_income_txns(personal_ids)

        def _totals(
            txns: list[dict[str, Any]],
        ) -> dict[str, int]:
            totals: dict[str, int] = {}
            for t in txns:
                totals[t["currency"]] = totals.get(t["currency"], 0) + t["amount"]
            return totals

        fop = _totals(fop_txns)
        personal = _totals(personal_txns)

        # Current balance per currency across personal accounts
        balance_rows = session.exec(
            select(Account.currency, func.sum(Account.balance))
            .where(Account.id.in_(personal_ids))
            .where(Account.hidden == False)  # noqa: E712
            .group_by(Account.currency)
        ).all()
        balances = {c: round(v) for c, v in balance_rows if v}

        # USD→UAH rate: pick highest exchange_rate value among FOP conversions
        # (rates > 1 are UAH/USD; rates < 1 are the inverse — skip those)
        fop_all_ids = session.exec(
            select(Account.id).where(Account.is_fop == True)  # noqa: E712
        ).all()
        rate_rows = session.exec(
            select(Transaction.extra)
            .where(Transaction.account_id.in_(fop_all_ids))
            .where(Transaction.extra.isnot(None))  # type: ignore[union-attr]
            .where(Transaction.date >= start)
            .where(Transaction.date <= end)
        ).all()
        usd_uah_rate: float | None = None
        for row in rate_rows:
            try:
                er = float(row["exchange_rate"])  # type: ignore[index]
                if er > 1 and (usd_uah_rate is None or er > usd_uah_rate):
                    usd_uah_rate = er
            except (KeyError, TypeError, ValueError):
                pass

        # Period start = earliest actual salary transaction date
        all_salary_dates = [
            date.fromisoformat(t["date"]) for t in fop_txns + personal_txns
        ]
        salary_start = min(all_salary_dates) if all_salary_dates else start

        all_currencies = sorted(set(fop) | set(personal))
        return {
            "period": date.today().strftime("%b %Y"),
            "period_start": salary_start.isoformat(),
            "period_end": end.isoformat(),
            "balances": balances,
            "usd_uah_rate": usd_uah_rate,
            "by_currency": {
                c: {
                    "fop": fop.get(c, 0),
                    "personal": personal.get(c, 0),
                    "fop_txns": [t for t in fop_txns if t["currency"] == c],
                    "personal_txns": [t for t in personal_txns if t["currency"] == c],
                }
                for c in all_currencies
            },
        }
