"""Helpers for manually labeling uncategorized transactions from chat."""

from typing import Any

from sqlmodel import Session, select

from finance_api.core.db.engine import engine
from finance_api.domains.transactions import categories as cat
from finance_api.domains.transactions import modes
from finance_api.domains.transactions.models import Transaction


def label_latest_uncategorized(description: str, category: str) -> dict[str, Any]:
    """Label the newest uncategorized transaction whose description matches."""
    if category not in cat.ALL:
        raise ValueError(f"Unknown category '{category}'. Valid: {sorted(cat.ALL)}")

    needle = description.strip().lower()
    if not needle:
        raise ValueError("Description is required")

    with Session(engine) as session:
        candidates = session.exec(
            select(Transaction)
            .where(Transaction.category.is_(None))  # type: ignore[union-attr]
            .order_by(Transaction.date.desc(), Transaction.created_at.desc())  # type: ignore[attr-defined]
            .limit(50)
        ).all()
        tx = next((t for t in candidates if needle in t.description.lower()), None)
        if tx is None:
            raise ValueError(f"No uncategorized transaction matches '{description}'")

        tx.category = category
        if tx.amount < 0 and tx.mode is None:
            tx.mode = modes.SOLO
        session.add(tx)
        session.commit()
        session.refresh(tx)
        return {
            "id": str(tx.id),
            "date": tx.date.isoformat(),
            "description": tx.description,
            "amount": tx.amount,
            "currency": tx.currency,
            "category": tx.category,
            "mode": tx.mode,
        }
