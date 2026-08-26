"""Credit ledger: balance calculation, admin adjustments, and the
double-spend race condition (spec Section 45)."""

import threading

from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.models import User
from app.services.credits import (
    InsufficientCreditsError,
    admin_adjust_credits,
    get_balance,
    spend_credits,
)


def _make_user(db: Session, username="alice") -> User:
    user = User(username=username, password_hash=hash_password("pw"))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_balance_starts_at_zero(db: Session) -> None:
    user = _make_user(db)
    assert get_balance(db, user.id) == 0


def test_admin_grant_and_deduction_affect_balance(db: Session) -> None:
    user = _make_user(db)
    admin_adjust_credits(db, user.id, 100, "grant")
    assert get_balance(db, user.id) == 100
    admin_adjust_credits(db, user.id, -30, "deduction")
    assert get_balance(db, user.id) == 70


def test_spend_credits_deducts_and_records_transaction(db: Session) -> None:
    user = _make_user(db)
    admin_adjust_credits(db, user.id, 50, "grant")
    spend_credits(db, user.id, 20, "sandbox instance")
    db.commit()
    assert get_balance(db, user.id) == 30


def test_spend_credits_rejects_insufficient_balance(db: Session) -> None:
    user = _make_user(db)
    admin_adjust_credits(db, user.id, 10, "grant")
    try:
        spend_credits(db, user.id, 20, "sandbox instance")
        assert False, "expected InsufficientCreditsError"
    except InsufficientCreditsError as e:
        assert e.required == 20
        assert e.available == 10
    db.rollback()
    assert get_balance(db, user.id) == 10


def test_concurrent_spend_cannot_double_spend(db: Session, db_session_factory) -> None:
    """Two concurrent 20-credit spend attempts against a 20-credit balance:
    exactly one must succeed. Verifies the SELECT ... FOR UPDATE row lock
    in spend_credits() actually serializes concurrent spenders for the
    same user, rather than both reading the pre-deduction balance."""
    user = _make_user(db)
    admin_adjust_credits(db, user.id, 20, "grant")

    results = []
    barrier = threading.Barrier(2)

    def attempt_spend():
        session = db_session_factory()
        try:
            barrier.wait()
            spend_credits(session, user.id, 20, "concurrent instance")
            session.commit()
            results.append("success")
        except InsufficientCreditsError:
            session.rollback()
            results.append("rejected")
        finally:
            session.close()

    threads = [threading.Thread(target=attempt_spend) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sorted(results) == ["rejected", "success"]
    assert get_balance(db, user.id) == 0
