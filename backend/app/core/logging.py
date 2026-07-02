"""Structured application logging.

Provides a configured root logger plus a small helper for emitting
domain events (AI requests, token usage, auth, scraping, errors) in a
consistent, greppable format.
"""
from __future__ import annotations

import logging
import sys

_CONFIGURED = False


def configure_logging(level: int = logging.INFO) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
    )
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [handler]
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)


def log_event(logger: logging.Logger, event: str, **fields: object) -> None:
    """Log a structured domain event, e.g.:

    log_event(log, "ai_request", user_id=1, tokens=320)
    """
    parts = " ".join(f"{k}={v}" for k, v in fields.items())
    logger.info("event=%s %s", event, parts)
