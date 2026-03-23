from airmodel import AirModel, AirField
from uuid import UUID
from datetime import datetime
from typing import Optional

class User(AirModel):
    id: Optional[UUID] = AirField(default=None, primary_key=True)
    email: str
    name: str
    bio: Optional[str] = None
    website: Optional[str] = None
    linkedin_url: Optional[str] = None
    qr_token: str
    password_hash: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class DanceCardEntry(AirModel):
    id: Optional[UUID] = AirField(default=None, primary_key=True)
    owner_id: UUID
    scanner_id: UUID
    created_at: Optional[datetime] = None
