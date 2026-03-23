import bcrypt
import secrets

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode(), salt).decode()

def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())

def create_session_cookie(user_id: str, secret_key: str) -> str:
    return f"{user_id}:{secrets.token_urlsafe(32)}"
