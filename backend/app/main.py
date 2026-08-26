"""
FastAPI application entrypoint.

Phase 1: boots the app with a health endpoint and a metrics endpoint so the
skeleton is deployable and observable end-to-end. Routers for auth,
instances, credits, admin, and the terminal WebSocket are added in their
respective phases (see README Roadmap) and wired up in `app/api/`.
"""

import logging

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.config import get_settings

settings = get_settings()

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("sandbox_platform")

app = FastAPI(
    title="DevOps/SRE Training Sandbox Platform API",
    version="0.1.0",
)


@app.get("/healthz", tags=["system"])
def healthz() -> dict:
    """Liveness/readiness probe target. Deliberately dependency-free so it
    reflects process health, not downstream service health."""
    return {"status": "ok"}


@app.get("/metrics", tags=["system"])
def metrics() -> PlainTextResponse:
    """Prometheus metrics endpoint. Counters for instance lifecycle, credit
    consumption, and API requests are registered in app/services as those
    phases land (see README Roadmap, Section 35 of the spec)."""
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# --- Routers (populated as each phase lands) ---
# from app.api import auth, instances, credits, admin, terminal
# app.include_router(auth.router, prefix="/api/v1")
# app.include_router(instances.router, prefix="/api/v1")
# app.include_router(credits.router, prefix="/api/v1")
# app.include_router(admin.router, prefix="/api/v1/admin")
# app.include_router(terminal.router)
