"""User-facing credit endpoints: balance + transaction history."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models import CreditTransaction, User
from app.schemas.credit import CreditBalanceOut, CreditTransactionOut
from app.services.credits import get_balance

router = APIRouter(tags=["credits"])


@router.get("/me/credits", response_model=CreditBalanceOut)
def read_my_balance(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> CreditBalanceOut:
    return CreditBalanceOut(balance=get_balance(db, user.id))


@router.get("/me/credits/history", response_model=list[CreditTransactionOut])
def read_my_credit_history(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[CreditTransaction]:
    return (
        db.query(CreditTransaction)
        .filter(CreditTransaction.user_id == user.id)
        .order_by(CreditTransaction.created_at.desc())
        .all()
    )
