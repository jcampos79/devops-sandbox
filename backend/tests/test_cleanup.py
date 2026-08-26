"""Expiration/cleanup task: issue -> confirm state transitions, idempotency,
and distinguishing EXPIRED vs TERMINATED (spec Section 14/15/46)."""

from datetime import timedelta
from unittest.mock import patch

from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.kubernetes.client import utcnow
from app.models import Distribution, Instance, InstanceStatus, User
from app.services.cleanup import run_cleanup_pass
from app.services.instances import issue_termination


def _make_user(db: Session, username="alice") -> User:
    user = User(username=username, password_hash=hash_password("pw"))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _make_instance(db: Session, user: User, *, expires_in_minutes: int, status=InstanceStatus.RUNNING) -> Instance:
    now = utcnow()
    instance = Instance(
        user_id=user.id,
        distribution=Distribution.ubuntu,
        status=status,
        namespace=f"sandbox-{user.username}",
        pod_name="sandbox",
        duration_minutes=10,
        credits_charged=10,
        created_at=now,
        expires_at=now + timedelta(minutes=expires_in_minutes),
    )
    db.add(instance)
    db.commit()
    db.refresh(instance)
    return instance


@patch("app.services.cleanup.k8s")
def test_expired_running_instance_issues_delete_and_becomes_terminating(mock_k8s, db: Session) -> None:
    user = _make_user(db)
    instance = _make_instance(db, user, expires_in_minutes=-5)  # already expired

    run_cleanup_pass()

    db.refresh(instance)
    assert instance.status == InstanceStatus.TERMINATING
    assert instance.deletion_issued_at is not None
    mock_k8s.delete_namespace.assert_called_once_with(instance.namespace)


@patch("app.services.cleanup.k8s")
def test_not_yet_expired_instance_is_left_alone(mock_k8s, db: Session) -> None:
    user = _make_user(db)
    instance = _make_instance(db, user, expires_in_minutes=30)

    run_cleanup_pass()

    db.refresh(instance)
    assert instance.status == InstanceStatus.RUNNING
    mock_k8s.delete_namespace.assert_not_called()


@patch("app.services.cleanup.k8s")
def test_terminating_instance_stays_terminating_while_namespace_still_exists(mock_k8s, db: Session) -> None:
    mock_k8s.namespace_exists.return_value = True
    user = _make_user(db)
    instance = _make_instance(db, user, expires_in_minutes=-5, status=InstanceStatus.TERMINATING)
    instance.deletion_issued_at = utcnow()
    db.commit()

    run_cleanup_pass()

    db.refresh(instance)
    assert instance.status == InstanceStatus.TERMINATING  # deletion still in progress
    assert instance.terminated_at is None


@patch("app.services.cleanup.k8s")
def test_expired_instance_confirmed_removed_becomes_expired(mock_k8s, db: Session) -> None:
    mock_k8s.namespace_exists.return_value = False
    user = _make_user(db)
    instance = _make_instance(db, user, expires_in_minutes=-10, status=InstanceStatus.TERMINATING)
    instance.deletion_issued_at = utcnow()  # issued after expires_at -> this was an expiration
    db.commit()

    run_cleanup_pass()

    db.refresh(instance)
    assert instance.status == InstanceStatus.EXPIRED
    assert instance.terminated_at is not None


@patch("app.services.instances.k8s")
@patch("app.services.cleanup.k8s")
def test_early_termination_confirmed_removed_becomes_terminated(mock_cleanup_k8s, mock_instances_k8s, db: Session) -> None:
    """Early termination issues delete before expires_at -- confirmed
    removal should land on TERMINATED, not EXPIRED."""
    mock_cleanup_k8s.namespace_exists.return_value = False
    user = _make_user(db)
    instance = _make_instance(db, user, expires_in_minutes=30, status=InstanceStatus.RUNNING)

    issue_termination(db, instance)  # issued well before expires_at
    run_cleanup_pass()

    db.refresh(instance)
    assert instance.status == InstanceStatus.TERMINATED
    assert instance.terminated_at is not None


@patch("app.services.cleanup.k8s")
def test_cleanup_pass_is_idempotent(mock_k8s, db: Session) -> None:
    mock_k8s.namespace_exists.return_value = False
    user = _make_user(db)
    instance = _make_instance(db, user, expires_in_minutes=-5)

    run_cleanup_pass()
    run_cleanup_pass()
    run_cleanup_pass()

    db.refresh(instance)
    assert instance.status == InstanceStatus.EXPIRED
