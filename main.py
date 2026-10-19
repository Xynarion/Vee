"""Uvicorn entrypoint: `uvicorn main:app --host 0.0.0.0 --port 8000`."""

from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()

from api.app import create_app  # noqa: E402

app = create_app()
