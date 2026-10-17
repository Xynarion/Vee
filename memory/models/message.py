from __future__ import annotations

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class Message(Base):
    __tablename__ = "messages"

    id = Column(String(64), primary_key=True)

    user_id = Column(String(64), ForeignKey("users.id"), nullable=False, index=True)
    user_channel_id = Column(String(64), ForeignKey("user_channels.id"), nullable=False, index=True)

    role = Column(
        Enum("user", "assistant", name="message_role_enum"),
        nullable=False,
    )

    text = Column(Text, nullable=False)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user = relationship("User", back_populates="messages")
    user_channel = relationship("UserChannel", back_populates="messages")

    __table_args__ = (
        Index("idx_messages_user_created", "user_id", "created_at"),
        Index("idx_messages_channel_created", "user_channel_id", "created_at"),
    )
