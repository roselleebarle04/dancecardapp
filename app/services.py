from typing import Optional
from app.models import User, DanceCardEntry

async def get_user_connections(user_id: int) -> list[tuple[str, Optional[str], Optional[str], Optional[str]]]:
    """Fetch all connections for a user with their details."""
    try:
        print("B44444", user_id)
        entries = await DanceCardEntry.filter(owner_id=user_id)
        print("A4444", entries)
        connection_details = []
        for entry in entries:
            scanner = await User.get(id=entry.scanner_id)
            if scanner:
                connection_details.append((scanner.name, scanner.bio, scanner.website, scanner.linkedin_url))
        return connection_details
    except Exception as e:
        print(f"get_user_connections error: {e}")
        return []
