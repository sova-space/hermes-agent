"""Helpers for loading transaction classification rules from the database."""

from sqlmodel import Session, select

from finance_api.core.db.engine import engine
from finance_api.domains.rules.models import TransactionRule


def get_patterns(rule_type: str) -> list[str]:
    """Return all patterns for the given rule type."""
    with Session(engine) as session:
        rows = session.exec(
            select(TransactionRule.pattern).where(
                TransactionRule.rule_type == rule_type
            )
        ).all()
        return list(rows)


def matches_any(description: str, patterns: list[str]) -> bool:
    """Return True if description contains any pattern (case-insensitive)."""
    lower = description.lower()
    return any(p.lower() in lower for p in patterns)
