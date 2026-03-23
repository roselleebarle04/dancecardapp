import os
import secrets
from fastapi import Cookie, HTTPException, status
import air
from dotenv import load_dotenv
from app.auth import hash_password, verify_password, create_session_cookie
from app.services import get_user_connections, get_or_create_dance_card_entry
from app.user_service import UserService
from app.utils import get_user_id_from_session

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
DOMAIN = os.getenv("RAILWAY_PUBLIC_DOMAIN", "")
ENVIRONMENT = os.getenv("RAILWAY_ENVIRONMENT_NAME", "development")
DEBUG = os.getenv("DEBUG", False)
PROTO = "https" if DEBUG else "http"

app = air.Air(debug=DEBUG)

from app.models import User, DanceCardEntry

@app.get("/")
async def landing(request: air.Request, session: str = Cookie(None)):
    user_id = get_user_id_from_session(session, SECRET_KEY) if SECRET_KEY else None

    if user_id:
        return air.RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)

    return app.jinja(request, "signup.html")

@app.post("/")
async def signup(request: air.Request):
    form_data = await request.form()
    email = form_data.get("email", "").strip()

    try:
        existing = await User.filter(email=email)

        if existing:
            return app.jinja(request, "signup.html", error="This email is already registered. Try logging in?", status_code=400)

        user = await UserService().create_user(email, form_data)
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
async def login_page(request: air.Request, session: str = Cookie(None)):
    user_id = get_user_id_from_session(session, SECRET_KEY) if SECRET_KEY else None

    if user_id:
        return air.RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)

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
        qr_code_url = f"{PROTO}://{DOMAIN}/s/{user.qr_token}"

        return app.jinja(request, "dashboard.html", user_name=user.name, qr_token=user.qr_token, qr_code_url=qr_code_url, connections=connections)
    except Exception:
        return air.RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

@app.get("/s/{token}")
async def view_qr_owner_profile(request: air.Request, token: str, session: str = Cookie(None)):
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
async def sign_up_as_scanner(request: air.Request, token: str):
    form_data = await request.form()
    email = form_data.get("email", "").strip()

    try:
        owner_users = await User.filter(qr_token=token)
        if not owner_users:
            raise HTTPException(status_code=404, detail="Invalid QR token")

        owner = owner_users[0]

        existing = await User.filter(email=email)

        if existing:
            return app.jinja(request, "scan_step1.html", owner_name=owner.name, token=token, error="This email is already registered.", status_code=400)

        scanner = await UserService().create_user(email, form_data)

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
async def add_owner_to_scanner_connections(request: air.Request, token: str, session: str = Cookie(None)):
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

@app.post("/s/{token}/add-to-my-card")
async def add_owner_to_my_dance_card(token: str, session: str = Cookie(None)):
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
