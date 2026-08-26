"""User-managed API key CRUD (spec Section 23)."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.security import generate_api_key
from app.database import get_db
from app.models import ApiKey, User
from app.schemas.api_key import ApiKeyCreate, ApiKeyCreated, ApiKeyOut

router = APIRouter(prefix="/me/api-keys", tags=["api-keys"])


@router.post("", response_model=ApiKeyCreated, status_code=status.HTTP_201_CREATED)
def create_api_key(
    payload: ApiKeyCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> ApiKeyCreated:
    plaintext, key_hash = generate_api_key()
    api_key = ApiKey(user_id=user.id, key_hash=key_hash, name=payload.name)
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    # The plaintext value is returned exactly once, here, and never again.
    return ApiKeyCreated(id=api_key.id, name=api_key.name, api_key=plaintext)


@router.get("", response_model=list[ApiKeyOut])
def list_api_keys(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[ApiKey]:
    return db.query(ApiKey).filter(ApiKey.user_id == user.id).order_by(ApiKey.created_at.desc()).all()


@router.delete("/{api_key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_key(
    api_key_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> None:
    api_key = db.get(ApiKey, api_key_id)
    if api_key is None or api_key.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "API key not found")
    api_key.revoked_at = datetime.now(timezone.utc)
    db.commit()
