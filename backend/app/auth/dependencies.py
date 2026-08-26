"""FastAPI auth dependencies. A single `get_current_user` accepts either a
session token (issued at login) or an API key via the same
`Authorization: Bearer <token>` header -- callers don't need to know which
kind they're presenting, and the platform doesn't need two separate auth
schemes wired through every router.
"""

from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.security import API_KEY_PREFIX, hash_api_key, verify_session_token
from app.database import get_db
from app.models import ApiKey, User

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing or invalid API key")

    token = credentials.credentials

    if token.startswith(API_KEY_PREFIX):
        user = _authenticate_api_key(token, db)
    else:
        user = _authenticate_session_token(token, db)

    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing or invalid API key")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is disabled")
    return user


def _authenticate_session_token(token: str, db: Session) -> User | None:
    user_id = verify_session_token(token)
    if user_id is None:
        return None
    return db.get(User, user_id)


def _authenticate_api_key(token: str, db: Session) -> User | None:
    key_hash = hash_api_key(token)
    api_key = db.query(ApiKey).filter(ApiKey.key_hash == key_hash).first()
    if api_key is None or api_key.is_revoked:
        return None
    api_key.last_used_at = datetime.now(timezone.utc)
    db.commit()
    return db.get(User, api_key.user_id)


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Administrator privileges required")
    return user
