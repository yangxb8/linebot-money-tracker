"""LINE webhook HMAC helpers for functional tests."""

from __future__ import annotations

import base64
import hashlib
import hmac


def sign_body(body: bytes, secret: str = "test_secret") -> str:
    """Return base64 HMAC-SHA256 digest for X-Line-Signature."""
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")
