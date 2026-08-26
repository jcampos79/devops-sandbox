"""Short-lived, single-use WebSocket terminal ticket tokens (spec Section
17). Kept as a small in-process store rather than a database table or
Redis: the backend runs as a single replica (see helm values
backend.replicas), ticket lifetimes are 30-60s, and losing outstanding
tickets on a restart is an acceptable, self-healing failure mode -- the
frontend just requests a new one.
"""

import secrets
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.config import get_settings

settings = get_settings()


@dataclass
class Ticket:
    token: str
    user_id: uuid.UUID
    instance_id: uuid.UUID
    expires_at: datetime
    used: bool = False


class TicketStore:
    """Thread-safe single-use ticket store. Never logs ticket values
    (spec Section 36)."""

    def __init__(self, ttl_seconds: int | None = None) -> None:
        self._ttl = ttl_seconds if ttl_seconds is not None else settings.ticket_ttl_seconds
        self._lock = threading.Lock()
        self._tickets: dict[str, Ticket] = {}

    def issue(self, user_id: uuid.UUID, instance_id: uuid.UUID) -> str:
        token = secrets.token_urlsafe(32)
        ticket = Ticket(
            token=token,
            user_id=user_id,
            instance_id=instance_id,
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=self._ttl),
        )
        with self._lock:
            self._tickets[token] = ticket
        return token

    def redeem(self, token: str, instance_id: uuid.UUID) -> uuid.UUID | None:
        """Validates ownership/expiry/not-already-used, then invalidates
        the ticket immediately. Returns the owning user_id on success."""
        with self._lock:
            ticket = self._tickets.get(token)
            if ticket is None:
                return None
            # Invalidate immediately regardless of outcome -- single use.
            del self._tickets[token]

        if ticket.used:
            return None
        if ticket.instance_id != instance_id:
            return None
        if datetime.now(timezone.utc) > ticket.expires_at:
            return None

        return ticket.user_id

    def _purge_expired(self) -> None:
        """Housekeeping helper; not required for correctness (redeem()
        already rejects expired tickets) but keeps the store from growing
        unbounded if tickets are issued and never redeemed."""
        now = datetime.now(timezone.utc)
        with self._lock:
            expired = [t for t, tk in self._tickets.items() if tk.expires_at < now]
            for t in expired:
                del self._tickets[t]


# Process-wide singleton -- the backend runs as a single replica.
ticket_store = TicketStore()
