"""Credit transaction ledger. The authoritative record of every credit
change -- balance is derived from this table, not a bare mutable field
(spec Section 12)."""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TransactionType(str, enum.Enum):
    ADMIN_GRANT = "ADMIN_GRANT"
    ADMIN_DEDUCTION = "ADMIN_DEDUCTION"
    INSTANCE_CREATE = "INSTANCE_CREATE"


class CreditTransaction(Base):
    __tablename__ = "credit_transactions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    instance_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("instances.id"), nullable=True
    )

    amount: Mapped[int] = mapped_column(Integer, nullable=False)  # positive or negative
    transaction_type: Mapped[TransactionType] = mapped_column(Enum(TransactionType), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
