"""Login and current-user endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.security import create_session_token, verify_password
from app.database import get_db
from app.models import User
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.user import MeOut
from app.services.credits import get_balance

logger = logging.getLogger("sandbox_platform")

router = APIRouter(tags=["auth"])


@router.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.username == payload.username).first()

    if user is None or not verify_password(payload.password, user.password_hash):
        logger.info("Login failed for username=%s", payload.username)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")

    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is disabled")

    logger.info("Login succeeded for user_id=%s", user.id)
    return TokenResponse(access_token=create_session_token(str(user.id)))


@router.get("/me", response_model=MeOut)
def read_me(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> MeOut:
    return MeOut(
        username=user.username,
        is_admin=user.is_admin,
        credit_balance=get_balance(db, user.id),
    )
