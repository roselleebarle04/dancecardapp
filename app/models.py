from dataclasses import dataclass
from datetime import datetime

@dataclass
class User:
    id: str
    email: str
    name: str
    bio: str = ""
    website: str = ""
    linkedin_url: str = ""
    qr_token: str = ""
    created_at: datetime = None

@dataclass
class DanceCardEntry:
    id: str
    owner_id: str
    scanner_id: str
    created_at: datetime = None
