"""Shared rate limiter (imported by main and by routes that need a tighter limit)."""
from __future__ import annotations

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def client_ip(request: Request) -> str:
    """Rate-limit key. Behind the Cloudflare Tunnel every request arrives from
    the tunnel process, so the socket address is the same for everyone; use
    the client address Cloudflare passes along. Safe to trust because the
    backend port is only published on 127.0.0.1 (reachable via the tunnel)."""
    return request.headers.get("cf-connecting-ip") or get_remote_address(request)


limiter = Limiter(key_func=client_ip, default_limits=["120/minute"])
