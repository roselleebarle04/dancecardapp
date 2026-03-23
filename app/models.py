from airmodel import AirModel, AirField
from datetime import datetime
from typing import Optional

class User(AirModel):
    id: Optional[int] = AirField(default=None, primary_key=True)
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
    id: Optional[int] = AirField(default=None, primary_key=True)
    owner_id: int
    scanner_id: int
    created_at: Optional[datetime] = None
