from typing import Optional

from app.auth import decode_session_cookie


def get_user_id_from_session(session: str, secret_key: str) -> Optional[int]:
    if not session or not secret_key:
        return None
    user_id_str = decode_session_cookie(session, secret_key)
    if not user_id_str:
        return None
    try:
        return int(user_id_str)
    except (ValueError, TypeError):
        return None
