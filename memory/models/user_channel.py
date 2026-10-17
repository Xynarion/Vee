from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class UserChannel(Base):
    __tablename__ = "user_channels"

    id = Column(String(64), primary_key=True)

    user_id = Column(String(64), ForeignKey("users.id"), nullable=False, index=True)

    platform = Column(
        Enum("telegram", "web", "whatsapp", "api", name="user_channel_platform_enum"),
        nullable=False,
    )

    platform_user_id = Column(String(128), nullable=False)

    is_primary = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user = relationship("User", back_populates="channels")
    messages = relationship("Message", back_populates="user_channel")

    __table_args__ = (
        UniqueConstraint("platform", "platform_user_id", name="uq_user_channels_platform_user"),
        Index("idx_user_channels_user_platform", "user_id", "platform"),
    )
