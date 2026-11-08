"""Encryption at rest: AES-256-GCM for uploaded files, exports, chat
messages, extracted document text and case summaries.

* Files on disk start with the magic ``FRC1`` followed by a 12-byte nonce
  and the GCM ciphertext. Files without the magic are legacy plaintext and
  are returned unchanged, so existing data keeps working; it is encrypted
  the next time it is written.
* Text columns hold ``enc1:<base64(nonce + ciphertext)>``; legacy plaintext
  is read as-is.
* The key is ``DATA_ENCRYPTION_KEY`` (32 random bytes, base64). Without it
  a key is derived from ``JWT_SECRET`` with HKDF -- acceptable for
  development, but set a dedicated key in production and back it up:
  losing it means losing the data.
"""
from __future__ import annotations

import base64
import json
import os
from functools import lru_cache

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator

from app.config import settings

FILE_MAGIC = b"FRC1"
TEXT_PREFIX = "enc1:"
_NONCE = 12


@lru_cache
def _aes() -> AESGCM:
    raw = settings.data_encryption_key.strip()
    if raw:
        key = base64.b64decode(raw)
        if len(key) != 32:
            raise RuntimeError("DATA_ENCRYPTION_KEY must be 32 bytes, base64-encoded")
    else:
        key = HKDF(
            algorithm=hashes.SHA256(), length=32, salt=b"francesca-data-at-rest",
            info=b"aes-256-gcm",
        ).derive(settings.jwt_secret.encode())
    return AESGCM(key)


# --- bytes / files ----------------------------------------------------------
def encrypt_bytes(data: bytes) -> bytes:
    nonce = os.urandom(_NONCE)
    return FILE_MAGIC + nonce + _aes().encrypt(nonce, data, FILE_MAGIC)


def decrypt_bytes(blob: bytes) -> bytes:
    if not blob.startswith(FILE_MAGIC):
        return blob  # legacy plaintext
    body = blob[len(FILE_MAGIC):]
    return _aes().decrypt(body[:_NONCE], body[_NONCE:], FILE_MAGIC)


def write_encrypted(path: str, data: bytes) -> None:
    with open(path, "wb") as fh:
        fh.write(encrypt_bytes(data))


def read_decrypted(path: str) -> bytes:
    with open(path, "rb") as fh:
        return decrypt_bytes(fh.read())


# --- text ---------------------------------------------------------------------
def encrypt_text(value: str) -> str:
    nonce = os.urandom(_NONCE)
    sealed = nonce + _aes().encrypt(nonce, value.encode("utf-8"), None)
    return TEXT_PREFIX + base64.b64encode(sealed).decode("ascii")


def decrypt_text(value: str) -> str:
    if not value.startswith(TEXT_PREFIX):
        return value  # legacy plaintext
    sealed = base64.b64decode(value[len(TEXT_PREFIX):])
    return _aes().decrypt(sealed[:_NONCE], sealed[_NONCE:], None).decode("utf-8")


class EncryptedText(TypeDecorator):
    """A Text column encrypted transparently on write, decrypted on read."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):  # noqa: ANN001
        return None if value is None else encrypt_text(str(value))

    def process_result_value(self, value, dialect):  # noqa: ANN001
        return None if value is None else decrypt_text(value)


class EncryptedJSON(TypeDecorator):
    """A JSON value stored encrypted. Kept in a JSON(B) column as a JSON
    string, so no column type change is needed; legacy objects read as-is."""

    impl = Text  # replaced per dialect in load_dialect_impl
    cache_ok = True

    def load_dialect_impl(self, dialect):  # noqa: ANN001
        from sqlalchemy import JSON
        from sqlalchemy.dialects.postgresql import JSONB

        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect):  # noqa: ANN001
        if value is None:
            return None
        return encrypt_text(json.dumps(value, ensure_ascii=False))

    def process_result_value(self, value, dialect):  # noqa: ANN001
        if isinstance(value, str) and value.startswith(TEXT_PREFIX):
            return json.loads(decrypt_text(value))
        return value
