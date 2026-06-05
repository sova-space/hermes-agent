"""Inline keyboard builders for the wishlist bot."""

from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard(wishlists: list[dict[str, Any]]) -> InlineKeyboardMarkup:
    """Build the main menu keyboard from a list of wishlist dicts."""
    rows = []
    for wl in wishlists:
        rows.append(
            [InlineKeyboardButton(wl["title"], callback_data=f"open:{wl['id']}")]
        )
    rows.append([InlineKeyboardButton("+ New Wishlist", callback_data="newlist")])
    return InlineKeyboardMarkup(rows)


def list_view_keyboard(wishlist_id: str) -> InlineKeyboardMarkup:
    """Build the list view keyboard for an owner."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "+ Add Item", callback_data=f"additem:{wishlist_id}"
                ),
                InlineKeyboardButton("Share", callback_data=f"share:{wishlist_id}"),
            ],
            [
                InlineKeyboardButton("Back", callback_data="menu"),
                InlineKeyboardButton(
                    "Delete List", callback_data=f"dellist:{wishlist_id}"
                ),
            ],
        ]
    )


def friend_view_keyboard(
    items: list[dict[str, Any]],
    viewer_telegram_id: int,
) -> InlineKeyboardMarkup:
    """Build the friend view keyboard with claim/unclaim buttons per item."""
    rows: list[list[InlineKeyboardButton]] = []
    for item in items:
        item_id = item["id"]
        if item["is_claimed"]:
            if item["claimed_by_telegram_id"] == viewer_telegram_id:
                rows.append(
                    [
                        InlineKeyboardButton(
                            f"Unclaim #{items.index(item) + 1}",
                            callback_data=f"unclaim:{item_id}",
                        )
                    ]
                )
        else:
            rows.append(
                [
                    InlineKeyboardButton(
                        f"I'll get #{items.index(item) + 1}",
                        callback_data=f"claim:{item_id}",
                    )
                ]
            )
    return InlineKeyboardMarkup(rows)


def main_menu_text(wishlists: list[dict[str, Any]], item_counts: dict[str, int]) -> str:
    """Build main menu message text."""
    if not wishlists:
        return "You have no wishlists yet."
    lines = ["Your wishlists:"]
    for wl in wishlists:
        count = item_counts.get(wl["id"], 0)
        noun = "item" if count == 1 else "items"
        lines.append(f"  {wl['title']} ({count} {noun})")
    return "\n".join(lines)


def list_view_text(wishlist: dict[str, Any], items: list[dict[str, Any]]) -> str:
    """Build list view message text for the owner."""
    lines = [f"{wishlist['title']}", ""]
    if not items:
        lines.append("No items yet.")
    for i, item in enumerate(items, start=1):
        parts = [f"{i}. {item['title']}"]
        if item["price"]:
            parts.append(item["price"])
        line = "  ".join(parts)
        if item["url"]:
            line += f"\n   {item['url']}"
        if item["is_claimed"]:
            line += f"\n   [Claimed by {item['claimed_by_name']}]"
        lines.append(line)
        rows_below = [
            InlineKeyboardButton(f"Remove #{i}", callback_data=f"remove:{item['id']}")
        ]
        _ = rows_below  # buttons are in the keyboard, text is here
    return "\n".join(lines)


def friend_view_text(wishlist: dict[str, Any], items: list[dict[str, Any]]) -> str:
    """Build friend view message text."""
    lines = [f"{wishlist['title']}", ""]
    if not items:
        lines.append("This wishlist is empty.")
    for i, item in enumerate(items, start=1):
        parts = [f"{i}. {item['title']}"]
        if item["price"]:
            parts.append(item["price"])
        line = "  ".join(parts)
        if item["url"]:
            line += f"\n   {item['url']}"
        if item["is_claimed"]:
            line += f"\n   Claimed by {item['claimed_by_name']}"
        lines.append(line)
    return "\n".join(lines)
