"""WebSocket terminal ticket issuance/validation/expiry/reuse-rejection
(spec Section 17/37)."""

import time
import uuid

from app.auth.tickets import TicketStore


def test_ticket_redeem_succeeds_for_matching_instance() -> None:
    store = TicketStore(ttl_seconds=30)
    user_id, instance_id = uuid.uuid4(), uuid.uuid4()
    token = store.issue(user_id, instance_id)
    assert store.redeem(token, instance_id) == user_id


def test_ticket_cannot_be_reused() -> None:
    store = TicketStore(ttl_seconds=30)
    user_id, instance_id = uuid.uuid4(), uuid.uuid4()
    token = store.issue(user_id, instance_id)
    assert store.redeem(token, instance_id) == user_id
    assert store.redeem(token, instance_id) is None  # second redemption rejected


def test_ticket_rejected_for_wrong_instance() -> None:
    store = TicketStore(ttl_seconds=30)
    user_id, instance_id = uuid.uuid4(), uuid.uuid4()
    token = store.issue(user_id, instance_id)
    assert store.redeem(token, uuid.uuid4()) is None


def test_ticket_expires() -> None:
    store = TicketStore(ttl_seconds=0)  # expires immediately
    user_id, instance_id = uuid.uuid4(), uuid.uuid4()
    token = store.issue(user_id, instance_id)
    time.sleep(0.01)
    assert store.redeem(token, instance_id) is None


def test_unknown_ticket_rejected() -> None:
    store = TicketStore(ttl_seconds=30)
    assert store.redeem("not-a-real-ticket", uuid.uuid4()) is None
