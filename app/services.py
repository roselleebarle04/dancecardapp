from typing import Optional
from uuid import UUID
from app.models import User, DanceCardEntry

async def get_user_connections(user_id: UUID) -> list[tuple[str, Optional[str], Optional[str], Optional[str]]]:
    """Fetch all connections for a user with their details."""
    entries = await DanceCardEntry.filter(owner_id=user_id)
    connection_details = []
    for entry in entries:
        scanner = await User.get(id=entry.scanner_id)
        if scanner:
            connection_details.append((scanner.name, scanner.bio, scanner.website, scanner.linkedin_url))
    return connection_details
