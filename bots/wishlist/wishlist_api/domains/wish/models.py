"""Wish domain models."""

import uuid
from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class WishUser(SQLModel, table=True):
    """A Telegram user who has interacted with the bot."""

    __tablename__ = "wish_users"

    telegram_id: int = Field(primary_key=True)
    first_name: str
    active_wishlist_id: uuid.UUID | None = None
    created_at: datetime = Field(default_factory=_utcnow)


class Wishlist(SQLModel, table=True):
    """A named wishlist owned by a user."""

    __tablename__ = "wishlists"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_telegram_id: int = Field(foreign_key="wish_users.telegram_id")
    title: str
    share_token: str = Field(unique=True)
    created_at: datetime = Field(default_factory=_utcnow)


class WishItem(SQLModel, table=True):
    """An item in a wishlist."""

    __tablename__ = "wish_items"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    wishlist_id: uuid.UUID = Field(foreign_key="wishlists.id")
    title: str
    url: str | None = None
    price: str | None = None
    is_claimed: bool = False
    claimed_by_name: str | None = None
    claimed_by_telegram_id: int | None = None
    created_at: datetime = Field(default_factory=_utcnow)
