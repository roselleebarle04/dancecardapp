from airmodel import AirModel, AirField
from uuid import UUID
from datetime import datetime

class User(AirModel):
    id: UUID | None = AirField(default=None, primary_key=True)
    email: str
    name: str
    bio: str | None = None
    website: str | None = None
    linkedin_url: str | None = None
    qr_token: str
    password_hash: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

class DanceCardEntry(AirModel):
    id: UUID | None = AirField(default=None, primary_key=True)
    owner_id: UUID
    scanner_id: UUID
    created_at: datetime | None = None
