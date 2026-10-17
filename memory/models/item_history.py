from __future__ import annotations

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Index, JSON, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class ItemHistory(Base):
    __tablename__ = "items_history"

    id = Column(String(64), primary_key=True)

    item_id = Column(String(64), ForeignKey("items.id"), nullable=False, index=True)
    message_id = Column(String(64), ForeignKey("messages.id"), nullable=True, index=True)

    kind = Column(
        Enum(
            "created",
            "updated",
            "completed",
            "carried",
            "cancelled",
            "dropped",
            name="item_history_kind_enum",
        ),
        nullable=False,
    )

    source = Column(
        Enum(
            "user_message",
            "assistant_inference",
            "daily_carryover",
            name="item_history_source_enum",
        ),
        nullable=False,
        default="user_message",
    )

    changes = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    item = relationship("Item", back_populates="history")

    __table_args__ = (
        Index("idx_history_item_kind", "item_id", "kind"),
        Index("idx_history_item_created", "item_id", "created_at"),
    )
