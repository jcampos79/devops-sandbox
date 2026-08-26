"""Administrator endpoints: users, credits, instances (spec Section 22).
Every route here requires require_admin -- an ordinary authenticated user
gets 403.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.auth.security import hash_password
from app.database import get_db
from app.models import CreditTransaction, Instance, User
from app.schemas.credit import AdminCreditAdjustment, CreditTransactionOut
from app.schemas.instance import InstanceOut
from app.schemas.user import UserCreate, UserOut
from app.services.credits import admin_adjust_credits, get_balance
from app.services.instances import issue_termination

router = APIRouter(dependencies=[Depends(require_admin)], tags=["admin"])


# --- Users ---


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)) -> list[User]:
    return db.query(User).order_by(User.created_at).all()


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Username already exists")
    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        is_admin=payload.is_admin,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _get_user_or_404(db: Session, user_id: uuid.UUID) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return user


@router.post("/users/{user_id}/disable", response_model=UserOut)
def disable_user(user_id: uuid.UUID, db: Session = Depends(get_db)) -> User:
    user = _get_user_or_404(db, user_id)
    user.is_active = False
    db.commit()
    db.refresh(user)
    return user


@router.post("/users/{user_id}/enable", response_model=UserOut)
def enable_user(user_id: uuid.UUID, db: Session = Depends(get_db)) -> User:
    user = _get_user_or_404(db, user_id)
    user.is_active = True
    db.commit()
    db.refresh(user)
    return user


# --- Credits ---


@router.post("/users/{user_id}/credits", response_model=CreditTransactionOut)
def adjust_credits(
    user_id: uuid.UUID, payload: AdminCreditAdjustment, db: Session = Depends(get_db)
) -> CreditTransaction:
    _get_user_or_404(db, user_id)
    return admin_adjust_credits(db, user_id, payload.amount, payload.description)


@router.get("/users/{user_id}/credits/history", response_model=list[CreditTransactionOut])
def user_credit_history(user_id: uuid.UUID, db: Session = Depends(get_db)) -> list[CreditTransaction]:
    _get_user_or_404(db, user_id)
    return (
        db.query(CreditTransaction)
        .filter(CreditTransaction.user_id == user_id)
        .order_by(CreditTransaction.created_at.desc())
        .all()
    )


# --- Instances ---


@router.get("/instances", response_model=list[InstanceOut])
def list_all_instances(db: Session = Depends(get_db)) -> list[Instance]:
    return db.query(Instance).order_by(Instance.created_at.desc()).all()


@router.get("/instances/{instance_id}", response_model=InstanceOut)
def get_any_instance(instance_id: uuid.UUID, db: Session = Depends(get_db)) -> Instance:
    instance = db.get(Instance, instance_id)
    if instance is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Instance not found")
    return instance


@router.delete("/instances/{instance_id}", response_model=InstanceOut)
def terminate_any_instance(instance_id: uuid.UUID, db: Session = Depends(get_db)) -> Instance:
    instance = db.get(Instance, instance_id)
    if instance is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Instance not found")
    return issue_termination(db, instance)
