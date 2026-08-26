import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.instance import Distribution, InstanceStatus


class InstanceCreate(BaseModel):
    distribution: Distribution
    duration_minutes: int = Field(ge=1, le=30)


class InstanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    distribution: Distribution
    status: InstanceStatus
    namespace: str
    pod_name: str
    duration_minutes: int
    credits_charged: int
    created_at: datetime
    expires_at: datetime
    terminated_at: datetime | None


class TerminalTicketOut(BaseModel):
    ticket: str
