"""Password hashing, session token signing, and API key generation/hashing.

Deliberately simple: no JWT library, no Redis-backed sessions. Session
tokens are signed+timestamped opaque strings (itsdangerous), verified
against BACKEND_SECRET_KEY; API keys are random tokens, stored only as a
SHA-256 hash (never plaintext -- spec Section 23).
"""

import hashlib
import secrets

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from passlib.context import CryptContext

from app.config import get_settings

settings = get_settings()

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SESSION_TOKEN_MAX_AGE_SECONDS = 60 * 60 * 12  # 12 hours
API_KEY_PREFIX = "sbx_"


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _pwd_context.verify(password, password_hash)


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.backend_secret_key, salt="session-token")


def create_session_token(user_id: str) -> str:
    return _serializer().dumps({"user_id": user_id})


def verify_session_token(token: str) -> str | None:
    """Returns the user_id encoded in the token, or None if invalid/expired."""
    try:
        data = _serializer().loads(token, max_age=SESSION_TOKEN_MAX_AGE_SECONDS)
    except (BadSignature, SignatureExpired):
        return None
    return data.get("user_id")


def generate_api_key() -> tuple[str, str]:
    """Returns (plaintext_key, key_hash). The plaintext is shown to the
    caller exactly once, at creation time, and never stored."""
    plaintext = f"{API_KEY_PREFIX}{secrets.token_urlsafe(32)}"
    return plaintext, hash_api_key(plaintext)


def hash_api_key(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()
