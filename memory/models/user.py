from __future__ import annotations

from sqlalchemy import Column, DateTime, Enum, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String(64), primary_key=True)

    name = Column(String(255), nullable=True)
    timezone = Column(String(64), nullable=False, default="Europe/London")

    status = Column(
        Enum("active", "paused", "deleted", name="user_status_enum"),
        nullable=False,
        default="active",
    )

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    channels = relationship("UserChannel", back_populates="user")
    messages = relationship("Message", back_populates="user")
    items = relationship("Item", back_populates="user")
