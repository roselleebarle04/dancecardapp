import bcrypt
from itsdangerous import URLSafeSerializer, BadSignature

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode(), salt).decode()

def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())

def create_session_cookie(user_id: str, secret_key: str) -> str:
    serializer = URLSafeSerializer(secret_key)
    return serializer.dumps({"user_id": user_id})

def decode_session_cookie(token: str, secret_key: str) -> str | None:
    serializer = URLSafeSerializer(secret_key)
    try:
        data = serializer.loads(token)
        return data.get("user_id")
    except BadSignature:
        return None
