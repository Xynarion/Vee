from __future__ import annotations

from sqlalchemy import Column, Date, DateTime, Enum, ForeignKey, Index, JSON, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class Item(Base):
    __tablename__ = "items"

    # --- core ---
    id = Column(String(64), primary_key=True)

    user_id = Column(String(64), ForeignKey("users.id"), nullable=False, index=True)

    type = Column(
        Enum("task", "event", name="item_type_enum"),
        nullable=False,
    )

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    parent_id = Column(String(64), ForeignKey("items.id"), nullable=True, index=True)

    start_at = Column(DateTime(timezone=True), nullable=True)
    end_at = Column(DateTime(timezone=True), nullable=True)
    due_at = Column(DateTime(timezone=True), nullable=True)

    status = Column(
        Enum(
            "todo",
            "in_progress",
            "blocked",
            "completed",
            "dropped",
            "cancelled",
            name="item_status_enum",
        ),
        nullable=False,
        default="todo",
    )

    work_mode = Column(
        Enum(
            "research",
            "building",
            "marketing",
            "personal",
            name="item_work_mode_enum",
        ),
        nullable=True,
        index=True,
    )

    flags = Column(JSON, nullable=False, default=list)
    carried_since = Column(Date, nullable=True)

    # --- meta ---
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user = relationship("User", back_populates="items")
    history = relationship("ItemHistory", back_populates="item")
    parent = relationship("Item", remote_side=[id])

    __table_args__ = (
        Index("idx_items_status", "user_id", "status"),
        Index("idx_items_user_due", "user_id", "due_at"),
        Index("idx_items_user_start", "user_id", "start_at"),
        Index("idx_items_user_carried", "user_id", "carried_since"),
        Index("idx_items_parent", "parent_id"),
    )
