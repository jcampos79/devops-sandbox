"""Instance lifecycle: duration validation, distribution validation, credit
deduction, and the CREATING -> RUNNING / ERROR transition on Kubernetes
failure. Mocks the Kubernetes client -- these tests don't require a real
cluster, but do exercise the real database transaction/locking path.
"""

from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.kubernetes.client import KubernetesUnavailableError
from app.models import Distribution, InstanceStatus, User
from app.services.credits import InsufficientCreditsError, admin_adjust_credits, get_balance
from app.services.instances import (
    InvalidDurationError,
    UnsupportedDistributionError,
    create_sandbox_instance,
)


def _make_user(db: Session, username="alice", balance=100) -> User:
    user = User(username=username, password_hash=hash_password("pw"))
    db.add(user)
    db.commit()
    db.refresh(user)
    if balance:
        admin_adjust_credits(db, user.id, balance, "test grant")
    return user


@patch("app.services.instances.k8s")
def test_create_instance_success(mock_k8s, db: Session) -> None:
    user = _make_user(db, balance=50)
    instance = create_sandbox_instance(db, user, Distribution.ubuntu, 20)

    assert instance.status == InstanceStatus.RUNNING
    assert instance.credits_charged == 20
    assert instance.namespace.startswith("sandbox-")
    assert get_balance(db, user.id) == 30
    mock_k8s.create_sandbox_namespace.assert_called_once_with(instance.namespace)
    mock_k8s.create_sandbox_pod.assert_called_once()


@patch("app.services.instances.k8s")
def test_create_instance_rejects_duration_over_30(mock_k8s, db: Session) -> None:
    user = _make_user(db)
    with pytest.raises(InvalidDurationError):
        create_sandbox_instance(db, user, Distribution.ubuntu, 60)
    mock_k8s.create_sandbox_namespace.assert_not_called()


@patch("app.services.instances.k8s")
def test_create_instance_rejects_duration_under_1(mock_k8s, db: Session) -> None:
    user = _make_user(db)
    with pytest.raises(InvalidDurationError):
        create_sandbox_instance(db, user, Distribution.ubuntu, 0)


@patch("app.services.instances.k8s")
def test_create_instance_insufficient_credits_does_not_provision(mock_k8s, db: Session) -> None:
    user = _make_user(db, balance=5)
    with pytest.raises(InsufficientCreditsError):
        create_sandbox_instance(db, user, Distribution.ubuntu, 20)
    mock_k8s.create_sandbox_namespace.assert_not_called()
    assert get_balance(db, user.id) == 5  # unchanged


@patch("app.services.instances.k8s")
def test_create_instance_cost_ignores_distribution(mock_k8s, db: Session) -> None:
    """Cost depends only on duration (spec Section 11) -- same duration,
    different distributions, same cost."""
    user = _make_user(db, balance=100)
    i1 = create_sandbox_instance(db, user, Distribution.ubuntu, 10)
    i2 = create_sandbox_instance(db, user, Distribution.alpine, 10)
    assert i1.credits_charged == i2.credits_charged == 10


@patch("app.services.instances.k8s")
def test_create_instance_kubernetes_failure_transitions_to_error(mock_k8s, db: Session) -> None:
    """Credits are already charged; a provisioning failure must not silently
    leave the instance stuck, nor pretend it's running (spec Section 16)."""
    mock_k8s.create_sandbox_namespace.side_effect = KubernetesUnavailableError("cluster unreachable")
    user = _make_user(db, balance=50)

    instance = create_sandbox_instance(db, user, Distribution.ubuntu, 15)

    assert instance.status == InstanceStatus.ERROR
    assert instance.error_message
    # Credits were already spent -- not refunded on ERROR (matches "no
    # refunds" policy; the ERROR state communicates the failure instead).
    assert get_balance(db, user.id) == 35
