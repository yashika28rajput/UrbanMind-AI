from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

from app.config import settings

TOKEN_TTL_SECONDS = 8 * 60 * 60
PASSWORD_ITERATIONS = 600_000


def authentication_configured() -> bool:
    return bool(
        settings.AUTH_USERNAME
        and settings.AUTH_PASSWORD_HASH
        and settings.AUTH_SECRET_KEY
        and len(settings.AUTH_SECRET_KEY) >= 32
    )


def auth_status() -> dict[str, bool]:
    return {
        "required": settings.AUTH_REQUIRED,
        "configured": authentication_configured(),
    }


def hash_password(password: str, salt: str | None = None) -> str:
    if not password:
        raise ValueError("Password must not be empty.")
    salt_text = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt_text.encode("utf-8"),
        PASSWORD_ITERATIONS,
    )
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt_text}${digest.hex()}"


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        algorithm, iteration_text, salt, expected = encoded_hash.split("$", 3)
        iterations = int(iteration_text)
        if algorithm != "pbkdf2_sha256" or not 100_000 <= iterations <= 2_000_000:
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations,
        ).hex()
    except (AttributeError, TypeError, ValueError):
        return False
    return hmac.compare_digest(actual, expected)


def _encode_segment(value: dict[str, Any]) -> str:
    raw = json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def create_access_token(username: str) -> str:
    if not authentication_configured():
        raise RuntimeError("Dashboard authentication is not configured.")
    issued_at = int(time.time())
    header = _encode_segment({"alg": "HS256", "typ": "JWT"})
    payload = _encode_segment({
        "sub": username,
        "iat": issued_at,
        "exp": issued_at + TOKEN_TTL_SECONDS,
    })
    signing_input = f"{header}.{payload}".encode("ascii")
    signature = hmac.new(
        settings.AUTH_SECRET_KEY.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).rstrip(b"=").decode("ascii")
    return f"{header}.{payload}.{encoded_signature}"


def token_subject(token: str) -> str | None:
    if not authentication_configured():
        return None
    try:
        header, payload, signature = token.split(".")
        signing_input = f"{header}.{payload}".encode("ascii")
        expected = hmac.new(
            settings.AUTH_SECRET_KEY.encode("utf-8"),
            signing_input,
            hashlib.sha256,
        ).digest()
        provided = base64.urlsafe_b64decode(signature + "=" * (-len(signature) % 4))
        if not hmac.compare_digest(expected, provided):
            return None
        decoded_header = json.loads(base64.urlsafe_b64decode(header + "=" * (-len(header) % 4)))
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        if decoded_header != {"alg": "HS256", "typ": "JWT"}:
            return None
        if int(claims.get("exp", 0)) <= int(time.time()):
            return None
        subject = claims.get("sub")
        return subject if isinstance(subject, str) and subject else None
    except (ValueError, TypeError, json.JSONDecodeError):
        return None


def verify_credentials(username: str, password: str) -> bool:
    if not authentication_configured():
        return False
    username_matches = hmac.compare_digest(username, settings.AUTH_USERNAME or "")
    password_matches = verify_password(password, settings.AUTH_PASSWORD_HASH or "")
    return username_matches and password_matches
