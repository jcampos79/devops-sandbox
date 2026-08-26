"""Sandbox instance model -- one row per ephemeral Linux sandbox, retained
after destruction as a historical record (spec Section 14)."""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Distribution(str, enum.Enum):
    ubuntu = "ubuntu"
    rocky = "rocky"
    debian = "debian"
    alpine = "alpine"


class InstanceStatus(str, enum.Enum):
    CREATING = "CREATING"
    RUNNING = "RUNNING"
    TERMINATING = "TERMINATING"
    TERMINATED = "TERMINATED"
    EXPIRED = "EXPIRED"
    ERROR = "ERROR"


class Instance(Base):
    __tablename__ = "instances"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)

    distribution: Mapped[Distribution] = mapped_column(Enum(Distribution), nullable=False)
    status: Mapped[InstanceStatus] = mapped_column(
        Enum(InstanceStatus), default=InstanceStatus.CREATING, nullable=False, index=True
    )

    namespace: Mapped[str] = mapped_column(String(63), unique=True, index=True, nullable=False)
    pod_name: Mapped[str] = mapped_column(String(63), nullable=False)

    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    credits_charged: Mapped[int] = mapped_column(Integer, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    terminated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Tracks the async issue/confirm deletion pattern (spec Section 14/46):
    # deletion_issued_at is set the moment namespace delete is called;
    # terminated_at is set only once removal is confirmed.
    deletion_issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
