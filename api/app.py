"""FastAPI application factory."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.telegram import client as telegram_client
from api.telegram.webhook import router as telegram_router

logger = logging.getLogger(__name__)


def _webhook_endpoint_url() -> str:
    base = (os.getenv("WEBHOOK_URL") or "").strip().rstrip("/")
    if not base:
        raise RuntimeError("WEBHOOK_URL is required (ngrok HTTPS origin, no path)")
    return f"{base}/telegram/webhook"


@asynccontextmanager
async def lifespan(app: FastAPI):
    secret = (os.getenv("TELEGRAM_WEBHOOK_SECRET") or "").strip()
    if not secret:
        raise RuntimeError("TELEGRAM_WEBHOOK_SECRET is required")
    url = _webhook_endpoint_url()
    await telegram_client.set_webhook(url=url, secret_token=secret)
    logger.info("Telegram webhook registered: %s", url)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Company Progress Memory", lifespan=lifespan)
    app.include_router(telegram_router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
