"""Initial schema: users, user_channels, messages, items, items_history.

Revision ID: 20261017_0001
Revises:
Create Date: 2026-10-17

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261017_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.Enum("active", "paused", "deleted", name="user_status_enum"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "user_channels",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("user_id", sa.String(length=64), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "platform",
            sa.Enum("telegram", "web", "whatsapp", "api", name="user_channel_platform_enum"),
            nullable=False,
        ),
        sa.Column("platform_user_id", sa.String(length=128), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("platform", "platform_user_id", name="uq_user_channels_platform_user"),
    )
    op.create_index("ix_user_channels_user_id", "user_channels", ["user_id"])
    op.create_index("idx_user_channels_user_platform", "user_channels", ["user_id", "platform"])

    op.create_table(
        "messages",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("user_id", sa.String(length=64), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("user_channel_id", sa.String(length=64), sa.ForeignKey("user_channels.id"), nullable=False),
        sa.Column(
            "role",
            sa.Enum("user", "assistant", name="message_role_enum"),
            nullable=False,
        ),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_messages_user_id", "messages", ["user_id"])
    op.create_index("ix_messages_user_channel_id", "messages", ["user_channel_id"])
    op.create_index("idx_messages_user_created", "messages", ["user_id", "created_at"])
    op.create_index("idx_messages_channel_created", "messages", ["user_channel_id", "created_at"])

    op.create_table(
        "items",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("user_id", sa.String(length=64), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "type",
            sa.Enum("task", "event", name="item_type_enum"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("parent_id", sa.String(length=64), sa.ForeignKey("items.id"), nullable=True),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "todo",
                "in_progress",
                "blocked",
                "completed",
                "dropped",
                "cancelled",
                name="item_status_enum",
            ),
            nullable=False,
        ),
        sa.Column(
            "work_mode",
            sa.Enum("research", "building", "marketing", "personal", name="item_work_mode_enum"),
            nullable=True,
        ),
        sa.Column("flags", sa.JSON(), nullable=False),
        sa.Column("carried_since", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_items_user_id", "items", ["user_id"])
    op.create_index("ix_items_parent_id", "items", ["parent_id"])
    op.create_index("ix_items_work_mode", "items", ["work_mode"])
    op.create_index("idx_items_status", "items", ["user_id", "status"])
    op.create_index("idx_items_user_due", "items", ["user_id", "due_at"])
    op.create_index("idx_items_user_start", "items", ["user_id", "start_at"])
    op.create_index("idx_items_user_carried", "items", ["user_id", "carried_since"])
    op.create_index("idx_items_parent", "items", ["parent_id"])

    op.create_table(
        "items_history",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("item_id", sa.String(length=64), sa.ForeignKey("items.id"), nullable=False),
        sa.Column("message_id", sa.String(length=64), sa.ForeignKey("messages.id"), nullable=True),
        sa.Column(
            "kind",
            sa.Enum(
                "created",
                "updated",
                "completed",
                "carried",
                "cancelled",
                "dropped",
                name="item_history_kind_enum",
            ),
            nullable=False,
        ),
        sa.Column(
            "source",
            sa.Enum(
                "user_message",
                "assistant_inference",
                "daily_carryover",
                name="item_history_source_enum",
            ),
            nullable=False,
        ),
        sa.Column("changes", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_items_history_item_id", "items_history", ["item_id"])
    op.create_index("ix_items_history_message_id", "items_history", ["message_id"])
    op.create_index("idx_history_item_kind", "items_history", ["item_id", "kind"])
    op.create_index("idx_history_item_created", "items_history", ["item_id", "created_at"])


def downgrade() -> None:
    op.drop_table("items_history")
    op.drop_table("items")
    op.drop_table("messages")
    op.drop_table("user_channels")
    op.drop_table("users")
