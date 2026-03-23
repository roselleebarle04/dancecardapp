from typing import Optional
from app.models import User, DanceCardEntry

async def get_user_connections(user_id: int) -> list[tuple[str, Optional[str], Optional[str], Optional[str]]]:
    """Fetch all connections for a user with their details."""
    entries = await DanceCardEntry.filter(owner_id=user_id)
    connection_details = []
    for entry in entries:
        scanner = await User.get(id=entry.scanner_id)
        if scanner:
            connection_details.append((scanner.name, scanner.bio, scanner.website, scanner.linkedin_url))
    return connection_details

async def get_or_create_dance_card_entry(owner_id: int, scanner_id: int) -> DanceCardEntry:
    """Get existing dance card entry or create a new one."""
    entries = await DanceCardEntry.filter(owner_id=owner_id, scanner_id=scanner_id)
    if entries:
        return entries[0]
    return await DanceCardEntry.create(owner_id=owner_id, scanner_id=scanner_id)
