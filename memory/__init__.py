"""Company progress memory.

Layout:
  types.py      — shared dataclasses (Turn)
  db.py         — engine, session, init_db
  models/       — SQLAlchemy schema (Alembic imports Base here)
  operations/   — relational ops (users, messages, ingress)
"""
