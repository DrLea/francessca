"""Shared Redis client used for caching and rate limiting."""
from __future__ import annotations

import redis

from app.config import settings

redis_client: redis.Redis = redis.from_url(
    settings.redis_url, encoding="utf-8", decode_responses=True
)
