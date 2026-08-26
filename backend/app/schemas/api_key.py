import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ApiKeyCreate(BaseModel):
    name: str


class ApiKeyCreated(BaseModel):
    """Returned only once, at creation time -- the plaintext key is never
    retrievable again afterward (spec Section 23)."""

    id: uuid.UUID
    name: str
    api_key: str


class ApiKeyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    created_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None
