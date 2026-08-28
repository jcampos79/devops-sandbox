"""Sandbox instance lifecycle: create, terminate, and the namespace-naming
scheme. This is the one place `create_sandbox_instance(...)` lives -- no
abstract instance-provider hierarchy (spec Section 43).
"""

import logging
import secrets
import uuid
from datetime import timedelta

from sqlalchemy.orm import Session

from app.config import get_settings
from app.kubernetes.client import KubernetesUnavailableError, k8s, utcnow
from app.models import Distribution, Instance, InstanceStatus, User
from app.services.credits import InsufficientCreditsError, spend_credits
from app.services.metrics import (
    sandbox_credits_consumed_total,
    sandbox_instance_creation_errors_total,
    sandbox_instances_active,
    sandbox_instances_created_total,
)

settings = get_settings()
logger = logging.getLogger("sandbox_platform")


class InvalidDurationError(Exception):
    pass


class UnsupportedDistributionError(Exception):
    pass


def _generate_namespace() -> str:
    """`sandbox-<unique-id>` -- users never choose this (spec Section 5)."""
    return f"{settings.sandbox_namespace_prefix}{secrets.token_hex(4)}"


def image_for(distribution: Distribution) -> str:
    image = settings.supported_distributions.get(distribution.value)
    if not image:
        raise UnsupportedDistributionError(distribution.value)
    return image


def shell_for(distribution: Distribution) -> str:
    return "/bin/sh" if distribution == Distribution.alpine else "/bin/bash"


def create_sandbox_instance(
    db: Session, user: User, distribution: Distribution, duration_minutes: int
) -> Instance:
    """Validates duration server-side (never trusts the frontend -- spec
    Section 13/44), deducts credits and creates the Instance row inside one
    transaction (spec Section 45), then provisions the namespace/pod. If
    Kubernetes provisioning fails after the DB transaction committed, the
    instance transitions to ERROR rather than silently charging credits
    with no explanation (spec Section 16)."""

    if not (1 <= duration_minutes <= settings.max_instance_duration_minutes):
        raise InvalidDurationError(
            f"duration_minutes must be between 1 and {settings.max_instance_duration_minutes}"
        )

    image = image_for(distribution)  # raises UnsupportedDistributionError early
    cost = duration_minutes  # 1 credit = 1 minute; cost never depends on resources (Section 11)
    namespace = _generate_namespace()
    now = utcnow()

    instance = Instance(
        user_id=user.id,
        distribution=distribution,
        status=InstanceStatus.CREATING,
        namespace=namespace,
        pod_name="sandbox",
        duration_minutes=duration_minutes,
        credits_charged=cost,
        created_at=now,
        expires_at=now + timedelta(minutes=duration_minutes),
    )

    # Steps 1-2 (spec Section 11): create the DB row and deduct credits in
    # a single transaction. spend_credits() takes SELECT ... FOR UPDATE on
    # the user row, so a concurrent request for the same user is blocked
    # until this transaction commits or rolls back (spec Section 45).
    db.add(instance)
    db.flush()  # assigns instance.id for the transaction's instance_id FK
    try:
        spend_credits(
            db,
            user_id=user.id,
            amount=cost,
            description=f"Sandbox instance ({distribution.value}, {duration_minutes}m)",
            instance_id=instance.id,
        )
    except InsufficientCreditsError:
        db.rollback()
        raise
    db.commit()
    db.refresh(instance)

    # Steps 3-5: provision Kubernetes resources. Credits are already spent
    # at this point -- if this fails, we mark ERROR rather than refund
    # (spec explicitly forbids refunds; ERROR communicates the failure).
    try:
        k8s.create_sandbox_namespace(namespace)
        k8s.create_sandbox_pod(
            namespace=namespace,
            pod_name=instance.pod_name,
            image=image,
            shell=shell_for(distribution),
        )
    except KubernetesUnavailableError as e:
        logger.error("Kubernetes provisioning failed for instance_id=%s: %s", instance.id, e)
        instance.status = InstanceStatus.ERROR
        instance.error_message = "Failed to provision sandbox environment"
        db.commit()
        db.refresh(instance)
        sandbox_instance_creation_errors_total.inc()
        return instance

    instance.status = InstanceStatus.RUNNING
    db.commit()
    db.refresh(instance)
    sandbox_instances_created_total.labels(distribution=distribution.value).inc()
    sandbox_instances_active.inc()
    sandbox_credits_consumed_total.inc(cost)
    logger.info(
        "Instance created: id=%s user_id=%s namespace=%s distribution=%s duration=%s",
        instance.id,
        user.id,
        namespace,
        distribution.value,
        duration_minutes,
    )
    return instance


def issue_termination(db: Session, instance: Instance) -> Instance:
    """Marks TERMINATING and issues namespace deletion. Confirmation of
    actual removal (-> TERMINATED) happens in the cleanup task, using the
    same issue/confirm pattern as expiration (spec Section 14/15/46). No
    credits are refunded for unused time."""
    if instance.status not in (InstanceStatus.RUNNING, InstanceStatus.CREATING):
        return instance

    instance.status = InstanceStatus.TERMINATING
    instance.deletion_issued_at = utcnow()
    db.commit()
    sandbox_instances_active.dec()

    try:
        k8s.delete_namespace(instance.namespace)
    except KubernetesUnavailableError as e:
        logger.error("Failed to issue namespace deletion for instance_id=%s: %s", instance.id, e)
        # Leave it in TERMINATING; the cleanup task will retry the delete
        # issue/confirm cycle on its next pass.

    db.refresh(instance)
    logger.info("Termination issued: instance_id=%s namespace=%s", instance.id, instance.namespace)
    return instance
