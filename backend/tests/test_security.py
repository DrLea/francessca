"""Tests for password hashing and JWT helpers."""
from __future__ import annotations

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip():
    hashed = hash_password("s3cret-password")
    assert hashed != "s3cret-password"
    assert verify_password("s3cret-password", hashed)
    assert not verify_password("wrong", hashed)


def test_long_password_over_72_bytes_does_not_raise():
    # bcrypt only uses the first 72 bytes; must not raise ValueError.
    long_pw = "a" * 200
    hashed = hash_password(long_pw)
    assert verify_password(long_pw, hashed)
    # First 72 bytes matching is expected bcrypt behaviour.
    assert verify_password("a" * 72, hashed)


def test_jwt_roundtrip():
    token = create_access_token(42, extra={"role": "admin"})
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "42"
    assert payload["role"] == "admin"


def test_jwt_invalid_returns_none():
    assert decode_access_token("not-a-jwt") is None
