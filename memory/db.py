"""Database engine and session lifecycle."""

from __future__ import annotations

import os
import uuid
from contextlib import contextmanager

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from memory.models import Base

load_dotenv()

_engine = None
_SessionLocal = None


def database_url() -> str:
    url = (os.getenv("DATABASE_URL") or "").strip()
    if not url:
        raise RuntimeError(
            "DATABASE_URL is required (e.g. postgresql+psycopg://memory:memory@127.0.0.1:5432/memory)"
        )
    return url


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(database_url(), pool_pre_ping=True)
    return _engine


def get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)
    return _SessionLocal


def init_db() -> None:
    """Dev-only bootstrap. Prefer: alembic upgrade head."""
    Base.metadata.create_all(bind=get_engine())


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


@contextmanager
def db_session() -> Session:
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
