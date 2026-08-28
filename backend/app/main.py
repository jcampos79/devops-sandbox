"""
FastAPI application entrypoint.

Phase 1: boots the app with a health endpoint and a metrics endpoint so the
skeleton is deployable and observable end-to-end. Routers for auth,
instances, credits, admin, and the terminal WebSocket are added in their
respective phases (see README Roadmap) and wired up in `app/api/`.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.config import get_settings

settings = get_settings()

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("sandbox_platform")


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.services.cleanup import start_cleanup_task

    start_cleanup_task()
    yield


app = FastAPI(
    title="DevOps/SRE Training Sandbox Platform API",
    version="0.1.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def count_requests(request: Request, call_next):
    """Increments sandbox_api_requests_total for every request (spec
    Section 35). Uses route.path (e.g. /api/v1/instances/{instance_id})
    rather than the raw URL so the label doesn't explode with one series
    per instance UUID."""
    response = await call_next(request)
    from app.services.metrics import sandbox_api_requests_total

    route = request.scope.get("route")
    path = route.path if route is not None else request.url.path
    sandbox_api_requests_total.labels(
        method=request.method, path=path, status_code=str(response.status_code)
    ).inc()
    return response


@app.exception_handler(HTTPException)
async def structured_http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Some endpoints raise HTTPException with a structured
    {"error": ..., "message": ...} body (spec Section 25). Return that body
    directly instead of FastAPI's default {"detail": ...} wrapper; plain
    string details still get a consistent {"error", "message"} shape."""
    if isinstance(exc.detail, dict):
        body = exc.detail
    else:
        body = {"error": exc.__class__.__name__, "message": str(exc.detail)}
    return JSONResponse(status_code=exc.status_code, content=body)


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


# --- Routers ---
from app.api import admin, api_keys, auth, credits, instances, terminal  # noqa: E402

app.include_router(auth.router, prefix="/api/v1")
app.include_router(credits.router, prefix="/api/v1")
app.include_router(instances.router, prefix="/api/v1")
app.include_router(api_keys.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1/admin")
app.include_router(terminal.router)
