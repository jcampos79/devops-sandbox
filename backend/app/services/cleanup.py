"""Background expiration/cleanup task (spec Section 14). A plain asyncio
task started at FastAPI startup -- no Celery/Redis/RabbitMQ/Kafka.

Runs every CLEANUP_INTERVAL_SECONDS and handles two responsibilities:
  1. Expired RUNNING instances: issue namespace deletion, transition to
     TERMINATING (mirrors issue_termination()).
  2. TERMINATING instances (from either expiration or user-initiated early
     termination): poll for confirmed namespace removal, then transition
     to EXPIRED or TERMINATED accordingly.

Idempotent and safe to run repeatedly: an already-deleted namespace is not
an error (see SandboxKubernetesClient.delete_namespace/namespace_exists).
"""

import asyncio
import logging

from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionLocal
from app.kubernetes.client import KubernetesUnavailableError, k8s, utcnow
from app.models import Instance, InstanceStatus
from app.services.metrics import (
    sandbox_instances_active,
    sandbox_instances_expired_total,
    sandbox_instances_terminated_total,
)

settings = get_settings()
logger = logging.getLogger("sandbox_platform")

_task: asyncio.Task | None = None


def start_cleanup_task() -> None:
    global _task
    if _task is None:
        _task = asyncio.create_task(_run_forever())


async def _run_forever() -> None:
    while True:
        try:
            run_cleanup_pass()
        except Exception:
            logger.exception("Cleanup pass failed")
        await asyncio.sleep(settings.cleanup_interval_seconds)


def run_cleanup_pass() -> None:
    db = SessionLocal()
    try:
        _issue_expired(db)
        _confirm_terminating(db)
    finally:
        db.close()


def _issue_expired(db: Session) -> None:
    now = utcnow()
    expired = (
        db.query(Instance)
        .filter(Instance.status == InstanceStatus.RUNNING, Instance.expires_at <= now)
        .all()
    )
    for instance in expired:
        instance.status = InstanceStatus.TERMINATING
        instance.deletion_issued_at = now
        db.commit()
        sandbox_instances_active.dec()
        try:
            k8s.delete_namespace(instance.namespace)
        except KubernetesUnavailableError as e:
            logger.error("Failed to issue delete for expired instance_id=%s: %s", instance.id, e)
        logger.info("Expiration issued: instance_id=%s namespace=%s", instance.id, instance.namespace)


def _confirm_terminating(db: Session) -> None:
    terminating = db.query(Instance).filter(Instance.status == InstanceStatus.TERMINATING).all()
    for instance in terminating:
        try:
            still_exists = k8s.namespace_exists(instance.namespace)
        except KubernetesUnavailableError as e:
            logger.error("Failed to check namespace removal for instance_id=%s: %s", instance.id, e)
            continue

        if still_exists:
            continue  # deletion still in progress; check again next pass

        # Confirmed removed. An instance that reached TERMINATING because
        # it expired becomes EXPIRED; one that was user/admin-terminated
        # early becomes TERMINATED. We distinguish by whether expires_at
        # had already passed at the moment deletion was issued.
        now = utcnow()
        if instance.deletion_issued_at and instance.deletion_issued_at >= instance.expires_at:
            instance.status = InstanceStatus.EXPIRED
            sandbox_instances_expired_total.inc()
        else:
            instance.status = InstanceStatus.TERMINATED
            sandbox_instances_terminated_total.inc()
        instance.terminated_at = now
        db.commit()
        logger.info(
            "Removal confirmed: instance_id=%s namespace=%s -> %s",
            instance.id,
            instance.namespace,
            instance.status.value,
        )
