"""FastAPI application entrypoint."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.api.routes import (
    admin,
    auth,
    case,
    chat,
    dashboard,
    files,
    lawyers,
    me,
    meta,
)
from app.config import settings
from app.core.logging import configure_logging, get_logger

configure_logging()
log = get_logger("francessca.app")

limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])

app = FastAPI(
    title="Francessca API",
    version="0.1.0",
    description=(
        "Francessca helps users prepare for speaking with a qualified lawyer. "
        "It is NOT a legal consultation platform and does not provide legal advice."
    ),
)

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


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    log.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok"}


for router in (auth, me, chat, files, lawyers, case, dashboard, admin, meta):
    app.include_router(router.router)
