"""Wish domain queries. All functions return plain dicts or None — never model instances."""

import secrets
import uuid
from typing import Any

import structlog
from sqlmodel import Session, select

from wishlist_api.domains.wish.models import WishItem, Wishlist, WishUser

log = structlog.get_logger(__name__)

_SHARE_TOKEN_BYTES = 9  # produces 12-char URL-safe base64 string


def _user_to_dict(user: WishUser) -> dict[str, Any]:
    return {
        "telegram_id": user.telegram_id,
        "first_name": user.first_name,
        "active_wishlist_id": str(user.active_wishlist_id)
        if user.active_wishlist_id
        else None,
        "created_at": user.created_at.isoformat(),
    }


def _wishlist_to_dict(wl: Wishlist) -> dict[str, Any]:
    return {
        "id": str(wl.id),
        "owner_telegram_id": wl.owner_telegram_id,
        "title": wl.title,
        "share_token": wl.share_token,
        "created_at": wl.created_at.isoformat(),
    }


def _item_to_dict(item: WishItem) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "wishlist_id": str(item.wishlist_id),
        "title": item.title,
        "url": item.url,
        "price": item.price,
        "is_claimed": item.is_claimed,
        "claimed_by_name": item.claimed_by_name,
        "claimed_by_telegram_id": item.claimed_by_telegram_id,
        "created_at": item.created_at.isoformat(),
    }


# ── User ──────────────────────────────────────────────────────────────────────


def upsert_user(session: Session, telegram_id: int, first_name: str) -> None:
    """Insert or update a user record."""
    user = session.get(WishUser, telegram_id)
    if user is None:
        user = WishUser(telegram_id=telegram_id, first_name=first_name)
        session.add(user)
        log.info("wish_user_created", telegram_id=telegram_id)
    else:
        user.first_name = first_name
        session.add(user)
    session.commit()


def get_user(session: Session, telegram_id: int) -> dict[str, Any] | None:
    """Return user dict or None if not found."""
    user = session.get(WishUser, telegram_id)
    return _user_to_dict(user) if user else None


def set_active_wishlist(
    session: Session, telegram_id: int, wishlist_id: uuid.UUID
) -> None:
    """Set the user's currently active wishlist."""
    user = session.get(WishUser, telegram_id)
    if user is None:
        return
    user.active_wishlist_id = wishlist_id
    session.add(user)
    session.commit()


# ── Wishlist ──────────────────────────────────────────────────────────────────


def create_wishlist(
    session: Session, owner_telegram_id: int, title: str
) -> dict[str, Any]:
    """Create a new wishlist and set it as the owner's active list."""
    wl = Wishlist(
        owner_telegram_id=owner_telegram_id,
        title=title,
        share_token=secrets.token_urlsafe(_SHARE_TOKEN_BYTES),
    )
    session.add(wl)
    session.commit()
    session.refresh(wl)
    # Set as active wishlist for the owner.
    set_active_wishlist(session, owner_telegram_id, wl.id)
    log.info("wishlist_created", wishlist_id=str(wl.id), owner=owner_telegram_id)
    return _wishlist_to_dict(wl)


def list_wishlists(session: Session, owner_telegram_id: int) -> list[dict[str, Any]]:
    """Return all wishlists owned by the user."""
    rows = session.exec(
        select(Wishlist).where(Wishlist.owner_telegram_id == owner_telegram_id)
    ).all()
    return [_wishlist_to_dict(wl) for wl in rows]


def get_wishlist_by_id(
    session: Session, wishlist_id: uuid.UUID
) -> dict[str, Any] | None:
    """Return wishlist dict by ID, or None if not found."""
    wl = session.get(Wishlist, wishlist_id)
    return _wishlist_to_dict(wl) if wl else None


def get_wishlist_by_token(session: Session, share_token: str) -> dict[str, Any] | None:
    """Return wishlist dict by share token, or None if not found."""
    wl = session.exec(
        select(Wishlist).where(Wishlist.share_token == share_token)
    ).first()
    return _wishlist_to_dict(wl) if wl else None


def delete_wishlist(session: Session, wishlist_id: uuid.UUID) -> bool:
    """Delete a wishlist and all its items. Returns False if not found."""
    wl = session.get(Wishlist, wishlist_id)
    if wl is None:
        return False
    items = session.exec(
        select(WishItem).where(WishItem.wishlist_id == wishlist_id)
    ).all()
    for item in items:
        session.delete(item)
    session.delete(wl)
    session.commit()
    log.info("wishlist_deleted", wishlist_id=str(wishlist_id))
    return True


# ── Items ─────────────────────────────────────────────────────────────────────


def add_item(
    session: Session,
    wishlist_id: uuid.UUID,
    title: str,
    price: str | None,
    url: str | None,
) -> dict[str, Any]:
    """Add an item to a wishlist."""
    item = WishItem(
        wishlist_id=wishlist_id,
        title=title,
        price=price,
        url=url,
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    log.info("wish_item_added", item_id=str(item.id), wishlist_id=str(wishlist_id))
    return _item_to_dict(item)


def list_items(session: Session, wishlist_id: uuid.UUID) -> list[dict[str, Any]]:
    """Return all items in a wishlist."""
    rows = session.exec(
        select(WishItem).where(WishItem.wishlist_id == wishlist_id)
    ).all()
    return [_item_to_dict(item) for item in rows]


def remove_item(session: Session, item_id: uuid.UUID) -> bool:
    """Delete a wish item. Returns False if not found."""
    item = session.get(WishItem, item_id)
    if item is None:
        return False
    session.delete(item)
    session.commit()
    log.info("wish_item_removed", item_id=str(item_id))
    return True


def claim_item(
    session: Session,
    item_id: uuid.UUID,
    claimer_name: str,
    claimer_telegram_id: int,
) -> dict[str, Any] | None:
    """Claim an item. Returns None if not found. Overwrites existing claim."""
    item = session.get(WishItem, item_id)
    if item is None:
        return None
    item.is_claimed = True
    item.claimed_by_name = claimer_name
    item.claimed_by_telegram_id = claimer_telegram_id
    session.add(item)
    session.commit()
    session.refresh(item)
    log.info("wish_item_claimed", item_id=str(item_id), claimer=claimer_telegram_id)
    return _item_to_dict(item)


def unclaim_item(
    session: Session,
    item_id: uuid.UUID,
    claimer_telegram_id: int,
) -> dict[str, Any] | None:
    """Unclaim an item. Returns None if not found or if caller is not the claimer."""
    item = session.get(WishItem, item_id)
    if item is None:
        return None
    if item.claimed_by_telegram_id != claimer_telegram_id:
        return None
    item.is_claimed = False
    item.claimed_by_name = None
    item.claimed_by_telegram_id = None
    session.add(item)
    session.commit()
    session.refresh(item)
    log.info("wish_item_unclaimed", item_id=str(item_id), claimer=claimer_telegram_id)
    return _item_to_dict(item)
