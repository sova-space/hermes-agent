# Spec 013 — Wishlist Bot

## Problem

Sharing a personal wishlist with friends and family for occasions like birthdays or holidays today requires a third-party app (Amazon Wishlist, Google Docs, etc.) or a messy shared message thread. Friends also duplicate efforts by buying the same gift when there is no coordination mechanism. There is no Telegram-native solution that lets someone quickly build a list and share it without leaving the chat.

## Solution

`@sova_wishlist_bot` — a public multi-user Telegram bot. Any Telegram user can:

1. Create named wishlists (e.g. "Birthday 2026", "Christmas").
2. Add items with optional price hint and optional URL.
3. Share a magic link with friends via a short token (`t.me/sova_wishlist_bot?start=view_<token>`).
4. Friends open the link in Telegram, browse the list, and claim items to signal they will buy them.
5. Owner sees claimed status so they never buy their own gift.

All navigation is via inline keyboard buttons. The only slash command is `/start`.

## Scope

**In scope:**
- Multi-user: any Telegram user can register and use the bot independently.
- Multiple wishlists per user.
- Items with title, optional free-text price, optional URL.
- Per-wishlist share links (12-char URL-safe token).
- Item claiming by friends (one claimer per item); unclaiming allowed.
- Main menu, list view, friend view — all as edited inline messages.

**Out of scope:**
- Notifications to owner when a friend claims an item.
- Item editing after creation (delete and re-add).
- Image/photo attachments to items.
- Expiry of wishlists or items.
- Analytics or admin endpoints beyond `/health` and `/bot/commands`.
- Payment or purchase tracking.

## User Flows

### Owner creates a wishlist

1. User sends `/start` → bot sends main menu: "You have no wishlists yet. [+ New Wishlist]"
2. User taps [+ New Wishlist] → bot sends "Enter wishlist name:" (ForceReply).
3. User replies with "Birthday 2026" → bot creates wishlist, shows list view (empty).

### Owner adds items

1. From list view, tap [+ Add Item].
2. Bot sends "Send item: title, optional ~price, optional URL" (ForceReply).
3. User replies with e.g. `Perfume ~$120 https://chanel.com`
4. Bot parses: title="Perfume", price="~$120", url="https://chanel.com".
5. Bot shows refreshed list view with the new item.

### Owner shares the list

1. From list view, tap [🔗 Share].
2. Bot sends: "Share this link with friends: `t.me/sova_wishlist_bot?start=view_<token>`"

### Friend views and claims

1. Friend opens share link in Telegram → bot handles `/start view_<token>`.
2. Bot shows friend view: items listed with [🎁 I'll get this] buttons.
3. Friend taps [🎁 I'll get this] → item shows "Claimed by \<name\>".
4. If the same friend claims twice, they see [↩ Unclaim] next to their item.
5. Other friends only see "Claimed by \<name\>" without unclaim option.

### Owner deletes a wishlist

1. From list view, tap [🗑 Delete] → wishlist is deleted, main menu shown.

## Data Model

- `wish_users` — `telegram_id` (PK), `first_name`, `active_wishlist_id`, `created_at`
- `wishlists` — `id` (UUID PK), `owner_telegram_id` (FK), `title`, `share_token` (unique), `created_at`
- `wish_items` — `id` (UUID PK), `wishlist_id` (FK), `title`, `url`, `price`, `is_claimed`, `claimed_by_name`, `claimed_by_telegram_id`, `created_at`

## Success Criteria

- `/start` responds in < 1 second and shows main menu.
- Creating a wishlist and adding 3 items takes under 30 seconds.
- Share link opens friend view correctly when tapped in Telegram.
- Friend claiming an item reflects immediately in the friend view.
- Owner and friend views are visually distinct and unambiguous.
- `/health` returns HTTP 200.
- Docker build and ruff checks pass.
- Smoke import test passes with dummy env vars.

## Open Questions

None — all resolved in the implementation plan.
