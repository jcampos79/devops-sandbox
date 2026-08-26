"""Instance REST API: create/list/get/delete (spec Section 24). Available
both to the web frontend (session token) and external API consumers (API
key) via the same get_current_user dependency -- see app/auth/dependencies.

A user can only see/manage their own instances (spec Section 26); admins
use the separate /api/v1/admin routes to act on any user's instances.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models import Instance, InstanceStatus, User
from app.schemas.instance import InstanceCreate, InstanceOut, TerminalTicketOut
from app.services.credits import InsufficientCreditsError
from app.services.instances import (
    InvalidDurationError,
    UnsupportedDistributionError,
    create_sandbox_instance,
    issue_termination,
)
from app.auth.tickets import ticket_store

logger = logging.getLogger("sandbox_platform")

router = APIRouter(prefix="/instances", tags=["instances"])


def _get_owned_instance(db: Session, user: User, instance_id: uuid.UUID) -> Instance:
    instance = db.get(Instance, instance_id)
    if instance is None or instance.user_id != user.id:
        # 404, not 403 -- don't reveal that another user's instance exists.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Instance not found")
    return instance


@router.post("", response_model=InstanceOut, status_code=status.HTTP_201_CREATED)
def create_instance(
    payload: InstanceCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Instance:
    try:
        return create_sandbox_instance(db, user, payload.distribution, payload.duration_minutes)
    except InvalidDurationError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e
    except UnsupportedDistributionError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unsupported distribution: {e}") from e
    except InsufficientCreditsError as e:
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            {
                "error": "insufficient_credits",
                "message": (
                    f"The instance requires {e.required} credits but the current "
                    f"balance is {e.available}."
                ),
            },
        ) from e


@router.get("", response_model=list[InstanceOut])
def list_instances(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[Instance]:
    return (
        db.query(Instance)
        .filter(Instance.user_id == user.id)
        .order_by(Instance.created_at.desc())
        .all()
    )


@router.get("/{instance_id}", response_model=InstanceOut)
def get_instance(
    instance_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Instance:
    return _get_owned_instance(db, user, instance_id)


@router.delete("/{instance_id}", response_model=InstanceOut)
def delete_instance(
    instance_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Instance:
    instance = _get_owned_instance(db, user, instance_id)
    return issue_termination(db, instance)


@router.post("/{instance_id}/terminal-ticket", response_model=TerminalTicketOut)
def create_terminal_ticket(
    instance_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> TerminalTicketOut:
    """Mints a short-lived, single-use WebSocket ticket for this instance
    (spec Section 17). The frontend calls this immediately before opening
    the terminal WebSocket."""
    instance = _get_owned_instance(db, user, instance_id)
    if instance.status != InstanceStatus.RUNNING:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Instance is not running")
    ticket = ticket_store.issue(user_id=user.id, instance_id=instance.id)
    return TerminalTicketOut(ticket=ticket)
