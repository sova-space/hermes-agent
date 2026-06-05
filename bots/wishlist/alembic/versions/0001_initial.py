"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-06-05
"""

import sqlalchemy as sa

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wish_users",
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("first_name", sa.String(), nullable=False),
        sa.Column("active_wishlist_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("telegram_id"),
    )

    op.create_table(
        "wishlists",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("share_token", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_telegram_id"], ["wish_users.telegram_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("share_token"),
    )
    op.create_index("ix_wishlists_share_token", "wishlists", ["share_token"], unique=True)
    op.create_index("ix_wishlists_owner", "wishlists", ["owner_telegram_id"])

    op.create_table(
        "wish_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("wishlist_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=True),
        sa.Column("price", sa.String(), nullable=True),
        sa.Column("is_claimed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("claimed_by_name", sa.String(), nullable=True),
        sa.Column("claimed_by_telegram_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["wishlist_id"], ["wishlists.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_wish_items_wishlist_id", "wish_items", ["wishlist_id"])


def downgrade() -> None:
    op.drop_index("ix_wish_items_wishlist_id", table_name="wish_items")
    op.drop_table("wish_items")
    op.drop_index("ix_wishlists_owner", table_name="wishlists")
    op.drop_index("ix_wishlists_share_token", table_name="wishlists")
    op.drop_table("wishlists")
    op.drop_table("wish_users")
