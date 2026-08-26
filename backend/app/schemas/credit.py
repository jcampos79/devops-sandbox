import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.credit_transaction import TransactionType


class CreditTransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    amount: int
    transaction_type: TransactionType
    description: str
    instance_id: uuid.UUID | None
    created_at: datetime


class CreditBalanceOut(BaseModel):
    balance: int


class AdminCreditAdjustment(BaseModel):
    amount: int  # positive to grant, negative to deduct
    description: str = ""
