"""WebSocket terminal endpoint. Ticket-authenticated (spec Section 17):
the browser must already hold a valid, unused, non-expired ticket for this
exact instance, minted by POST /api/v1/instances/{id}/terminal-ticket.
"""

import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.auth.tickets import ticket_store
from app.database import SessionLocal
from app.models import Instance, InstanceStatus
from app.services.instances import shell_for
from app.terminal.exec_bridge import bridge_terminal

logger = logging.getLogger("sandbox_platform")

router = APIRouter(tags=["terminal"])


@router.websocket("/ws/instances/{instance_id}/terminal")
async def terminal_websocket(websocket: WebSocket, instance_id: uuid.UUID, ticket: str) -> None:
    user_id = ticket_store.redeem(ticket, instance_id)
    if user_id is None:
        await websocket.close(code=4401, reason="Invalid, expired, or already-used ticket")
        return

    db: Session = SessionLocal()
    try:
        instance = db.get(Instance, instance_id)
        if instance is None or instance.user_id != user_id:
            await websocket.close(code=4404, reason="Instance not found")
            return
        if instance.status != InstanceStatus.RUNNING:
            await websocket.close(code=4409, reason="Instance is not running")
            return

        await websocket.accept()
        logger.info("Terminal connected: instance_id=%s user_id=%s", instance_id, user_id)
        try:
            await bridge_terminal(
                websocket,
                namespace=instance.namespace,
                pod_name=instance.pod_name,
                shell=shell_for(instance.distribution),
            )
        except WebSocketDisconnect:
            pass
        finally:
            logger.info("Terminal disconnected: instance_id=%s user_id=%s", instance_id, user_id)
    finally:
        db.close()
