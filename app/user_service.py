import secrets

from app.auth import hash_password
from app.models import User


class UserService:

    @staticmethod
    async def create_user(email, form_data):
        name = form_data.get("name", "").strip()
        bio = form_data.get("bio", "").strip()
        website = form_data.get("website", "").strip()
        linkedin_url = form_data.get("linkedin_url", "").strip()
        password = form_data.get("password", "")

        if linkedin_url and not linkedin_url.startswith(("http://", "https://")):
            linkedin_url = f"https://linkedin.com/in/{linkedin_url}"

        qr_token = secrets.token_urlsafe(6)[:6].upper()
        password_hash = hash_password(password)

        return await User.create(
            email=email,
            name=name,
            bio=bio or None,
            website=website or None,
            linkedin_url=linkedin_url or None,
            qr_token=qr_token,
            password_hash=password_hash
        )
