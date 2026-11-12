"""FastAPI application entrypoint."""
from __future__ import annotations

import os

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.routes import (
    admin,
    auth,
    case,
    chat,
    dashboard,
    files,
    lawyer_portal,
    lawyers,
    me,
    meta,
    orders,
    public,
    reports,
)
from app.config import settings
from app.core.logging import configure_logging, get_logger
from app.core.ratelimit import limiter

configure_logging()
log = get_logger("francessca.app")

app = FastAPI(
    title="Francesca API",
    version="0.1.0",
    description=(
        "Francesca helps users prepare for speaking with a qualified lawyer. "
        "It is NOT a legal consultation platform and does not provide legal advice."
    ),
    docs_url="/docs" if settings.enable_docs else None,
    redoc_url="/redoc" if settings.enable_docs else None,
    openapi_url="/openapi.json" if settings.enable_docs else None,
)

@app.on_event("startup")
async def _start_reminders() -> None:
    import asyncio

    from app.services.reminder_service import reminder_loop

    if settings.reminders_enabled:
        app.state.reminder_task = asyncio.create_task(reminder_loop())


app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(httpx.TimeoutException)
async def model_timeout_handler(request: Request, exc: Exception) -> JSONResponse:
    """A local model that ran out of time is an expected condition, not a
    crash: say so plainly instead of dumping a traceback into the log."""
    log.warning("Model timed out on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=504,
        content={
            "detail": (
                "The local model took too long to answer. Try a smaller model "
                "(ollama pull qwen2.5:7b) or a shorter document."
            )
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    log.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok"}


if settings.api_prefix.strip("/"):
    # Same check, reachable through a proxy that only forwards /api/*.
    app.add_api_route(
        f"/{settings.api_prefix.strip('/')}/health", health, methods=["GET"], tags=["meta"]
    )


# The API and the UI have pages with the same names -- /chat, /lawyers,
# /files, /dashboard, /timeline. On separate origins that is fine; in the
# desktop build they share one, and the API route would shadow the page (the
# browser asking for /chat got {"detail":"Not authenticated"}). So when this
# process also serves the UI, the whole API moves under /api.
API_PREFIX = (
    "/" + settings.api_prefix.strip("/")
    if settings.api_prefix.strip("/")
    else ("/api" if settings.frontend_dist else "")
)

for router in (
    auth,
    me,
    chat,
    files,
    lawyers,
    lawyer_portal,
    orders,
    case,
    dashboard,
    admin,
    meta,
    public,
    reports,
):
    app.include_router(router.router, prefix=API_PREFIX)


# --- Desktop build: serve the exported frontend from the same process ----
# Mounted last, so every API route above still wins. StaticFiles(html=True)
# resolves "/chat/" to "chat/index.html", which is why the desktop frontend
# is exported with trailing slashes.
if settings.frontend_dist and os.path.isdir(settings.frontend_dist):
    app.mount(
        "/", StaticFiles(directory=settings.frontend_dist, html=True), name="frontend"
    )
    log.info("Serving frontend from %s", settings.frontend_dist)
