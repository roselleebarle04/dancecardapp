import os
import secrets
from typing import Optional
from fastapi import Cookie, HTTPException, status
import air
from dotenv import load_dotenv
from app.auth import hash_password, verify_password, create_session_cookie, decode_session_cookie
from app.services import get_user_connections, get_or_create_dance_card_entry

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
DOMAIN = os.getenv("DOMAIN")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

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

app = air.Air(debug=True)

from app.models import User, DanceCardEntry

@app.get("/")
async def landing(request: air.Request):
    return app.jinja(request, "signup.html")

@app.post("/")
async def signup(request: air.Request):
    form_data = await request.form()
    email = form_data.get("email", "").strip()
    name = form_data.get("name", "").strip()
    bio = form_data.get("bio", "").strip()
    website = form_data.get("website", "").strip()
    linkedin_url = form_data.get("linkedin_url", "").strip()
    password = form_data.get("password", "")

    try:
        existing = await User.filter(email=email)
        if existing:
            return app.jinja(request, "signup.html", error="This email is already registered. Try logging in?", status_code=400)

        qr_token = secrets.token_urlsafe(6)[:6].upper()
        password_hash = hash_password(password)

        user = await User.create(
            email=email,
            name=name,
            bio=bio or None,
            website=website or None,
            linkedin_url=linkedin_url or None,
            qr_token=qr_token,
            password_hash=password_hash
        )

        response = air.RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(
            "session",
            value=create_session_cookie(str(user.id), SECRET_KEY),
            httponly=True,
            samesite="Lax"
        )
        return response
    except Exception as e:
        print(e)
        return app.jinja(request, "signup.html", error="Error creating account. Please try again.", status_code=500)

@app.get("/login")
async def login_page(request: air.Request):
    return app.jinja(request, "login.html")

@app.post("/login")
async def login(request: air.Request):
    form_data = await request.form()
    email = form_data.get("email", "").strip()
    password = form_data.get("password", "")

    try:
        users = await User.filter(email=email)
        if not users:
            return app.jinja(request, "login.html", error="Incorrect email or password.", status_code=401)

        user = users[0]
        if not verify_password(password, user.password_hash):
            return app.jinja(request, "login.html", error="Incorrect email or password.", status_code=401)

        response = air.RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(
            "session",
            value=create_session_cookie(str(user.id), SECRET_KEY),
            httponly=True,
            samesite="Lax"
        )
        return response
    except Exception:
        return app.jinja(request, "login.html", error="Error during login. Please try again.", status_code=500)

@app.post("/logout")
async def logout():
    response = air.RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("session")
    return response

@app.get("/dashboard")
async def dashboard(request: air.Request, session: str = Cookie(None)):
    user_id = get_user_id_from_session(session, SECRET_KEY)

    if not user_id:
        return air.RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    try:
        user = await User.get(id=user_id)
        if not user:
            return air.RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

        connections = await get_user_connections(user_id)
        qr_code_url = f"https://{DOMAIN}/s/{user.qr_token}"

        return app.jinja(request, "dashboard.html", user_name=user.name, qr_token=user.qr_token, qr_code_url=qr_code_url, connections=connections)
    except Exception:
        return air.RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

@app.get("/s/{token}")
async def scan_step1(request: air.Request, token: str, session: str = Cookie(None)):
    try:
        users = await User.filter(qr_token=token)

        if not users:
            return app.jinja(request, "error.html", message="Invalid share link. Try again?", status_code=404)

        owner = users[0]
        user_id = get_user_id_from_session(session, SECRET_KEY) if SECRET_KEY else None

        if user_id:
            entries = await DanceCardEntry.filter(owner_id=owner.id, scanner_id=user_id)
            if entries:
                return app.jinja(request, "scan_step4.html", owner_name=owner.name, token=token, owner_id=owner.id)
            return app.jinja(request, "scan_step3.html", owner_name=owner.name, token=token, is_logged_in=True)

        return app.jinja(request, "scan_step1.html", owner_name=owner.name, token=token)
    except Exception:
        return app.jinja(request, "error.html", message="Error loading share link.", status_code=500)

@app.post("/s/{token}")
async def scan_step2(request: air.Request, token: str):
    form_data = await request.form()
    email = form_data.get("email", "").strip()
    name = form_data.get("name", "").strip()
    bio = form_data.get("bio", "").strip()
    website = form_data.get("website", "").strip()
    linkedin_url = form_data.get("linkedin_url", "").strip()
    password = form_data.get("password", "")

    try:
        owner_users = await User.filter(qr_token=token)
        if not owner_users:
            raise HTTPException(status_code=404, detail="Invalid QR token")

        owner = owner_users[0]

        existing = await User.filter(email=email)
        if existing:
            return app.jinja(request, "scan_step1.html", owner_name=owner.name, token=token, error="This email is already registered.", status_code=400)

        qr_token = secrets.token_urlsafe(6)[:6].upper()
        password_hash = hash_password(password)

        scanner = await User.create(
            email=email,
            name=name,
            bio=bio or None,
            website=website or None,
            linkedin_url=linkedin_url or None,
            qr_token=qr_token,
            password_hash=password_hash
        )

        await get_or_create_dance_card_entry(owner_id=owner.id, scanner_id=scanner.id)

        response = app.jinja(request, "scan_step4.html", owner_name=owner.name, token=token, owner_id=owner.id)
        response.set_cookie(
            "session",
            value=create_session_cookie(str(scanner.id), SECRET_KEY),
            httponly=True,
            samesite="Lax"
        )
        return response
    except Exception:
        return app.jinja(request, "scan_step1.html", error="Error processing signup.", status_code=500)

@app.post("/s/{token}/add")
async def scan_step3(request: air.Request, token: str, session: str = Cookie(None)):
    scanner_id = get_user_id_from_session(session, SECRET_KEY)
    if not scanner_id:
        return air.RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)

    try:
        owner_users = await User.filter(qr_token=token)
        if not owner_users:
            raise HTTPException(status_code=404, detail="Invalid QR token")

        owner = owner_users[0]

        await get_or_create_dance_card_entry(owner_id=owner.id, scanner_id=scanner_id)

        return app.jinja(request, "scan_step4.html", owner_name=owner.name, token=token, owner_id=owner.id)
    except Exception:
        return air.RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)

@app.post("/s/{token}/reciprocal")
async def add_reciprocal(token: str, session: str = Cookie(None)):
    scanner_id = get_user_id_from_session(session, SECRET_KEY) if SECRET_KEY else None
    if not scanner_id:
        return air.RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)

    try:
        owner_users = await User.filter(qr_token=token)
        if not owner_users:
            raise HTTPException(status_code=404, detail="Invalid QR token")

        owner = owner_users[0]

        await get_or_create_dance_card_entry(owner_id=scanner_id, scanner_id=owner.id)

        return air.RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    except Exception:
        return air.RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
