"""Credit ledger: balance calculation and concurrency-safe spending.

Balance is always derived from the transaction ledger (spec Section 12) --
there is no separate mutable balance column to drift out of sync.

`spend_credits` is the only path that deducts credits for instance
creation, and it is the piece responsible for making concurrent creation
requests unable to double-spend the same balance (spec Section 45):
it takes `SELECT ... FOR UPDATE` on the user's row inside the caller's
transaction, so a second concurrent request blocks until the first
transaction commits or rolls back, and then re-reads a balance that
already reflects the first request's deduction.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import CreditTransaction, TransactionType, User


class InsufficientCreditsError(Exception):
    def __init__(self, required: int, available: int) -> None:
        self.required = required
        self.available = available
        super().__init__(f"requires {required} credits but balance is {available}")


def get_balance(db: Session, user_id: uuid.UUID) -> int:
    total = db.scalar(
        select(func.coalesce(func.sum(CreditTransaction.amount), 0)).where(
            CreditTransaction.user_id == user_id
        )
    )
    return int(total or 0)


def lock_user_for_update(db: Session, user_id: uuid.UUID) -> User:
    """Takes a row lock on the user, blocking concurrent callers of this
    function for the same user until the current transaction ends. Must be
    called within an open transaction; the caller commits or rolls back."""
    return db.execute(select(User).where(User.id == user_id).with_for_update()).scalar_one()


def spend_credits(
    db: Session,
    user_id: uuid.UUID,
    amount: int,
    description: str,
    instance_id: uuid.UUID | None = None,
) -> CreditTransaction:
    """Deducts `amount` credits if the user has sufficient balance, as one
    atomic, row-locked operation. Raises InsufficientCreditsError without
    writing anything if the balance is insufficient. Does NOT commit --
    the caller controls the transaction boundary so this can be combined
    with other writes (e.g. creating the Instance row) atomically."""
    lock_user_for_update(db, user_id)  # blocks concurrent spenders for this user
    balance = get_balance(db, user_id)

    if balance < amount:
        raise InsufficientCreditsError(required=amount, available=balance)

    txn = CreditTransaction(
        user_id=user_id,
        instance_id=instance_id,
        amount=-amount,
        transaction_type=TransactionType.INSTANCE_CREATE,
        description=description,
    )
    db.add(txn)
    db.flush()
    return txn


def admin_adjust_credits(
    db: Session, user_id: uuid.UUID, amount: int, description: str
) -> CreditTransaction:
    """Admin grant (amount > 0) or deduction (amount < 0). Not subject to
    the same race conditions as instance creation since admin actions are
    infrequent and don't need to reject on insufficient balance -- an
    admin deduction is allowed to take a balance negative if an operator
    explicitly does that (matches spec Section 12/22, which places no
    floor on admin deductions)."""
    txn = CreditTransaction(
        user_id=user_id,
        amount=amount,
        transaction_type=TransactionType.ADMIN_GRANT if amount >= 0 else TransactionType.ADMIN_DEDUCTION,
        description=description,
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)
    return txn
