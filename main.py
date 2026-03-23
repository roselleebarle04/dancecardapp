import os
import secrets
from contextlib import asynccontextmanager
from fastapi import Cookie, HTTPException, status
import air
from dotenv import load_dotenv
from app.db import init_db, get_db_connection
from app.auth import hash_password, verify_password, create_session_cookie
from app.qrcode_gen import generate_qr_code

load_dotenv()

PSYCOPG_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY")
DOMAIN = os.getenv("DOMAIN")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

@asynccontextmanager
async def lifespan(app):
    await init_db()
    yield

app = air.Air(lifespan=lifespan)

@app.get("/")
async def landing(request: air.Request):
    return app.jinja(request, "signup.html")

@app.post("/")
async def signup(request: air.Request):
    form_data = await request.form()
    email = form_data.get("email")
    name = form_data.get("name")
    bio = form_data.get("bio", "")
    website = form_data.get("website", "")
    linkedin_url = form_data.get("linkedin_url", "")
    password = form_data.get("password")

    db = get_db_connection()
    cursor = db.cursor()

    try:
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            return app.jinja(request, "signup.html", error="This email is already registered. Try logging in?", status_code=400)

        qr_token = secrets.token_urlsafe(6)[:6].upper()
        password_hash = hash_password(password)

        cursor.execute(
            "INSERT INTO users (email, name, bio, website, linkedin_url, qr_token, password_hash) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
            (email, name, bio, website, linkedin_url, qr_token, password_hash)
        )
        user_id = cursor.fetchone()[0]
        db.commit()

        response = air.RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(
            "session",
            value=create_session_cookie(str(user_id), SECRET_KEY),
            httponly=True,
            samesite="Lax"
        )
        return response
    except Exception:
        db.rollback()
        return app.jinja(request, "signup.html", error="Error creating account. Please try again.", status_code=500)
    finally:
        cursor.close()
        db.close()

@app.get("/login")
async def login_page(request: air.Request):
    return app.jinja(request, "login.html")

@app.post("/login")
async def login(request: air.Request):
    form_data = await request.form()
    email = form_data.get("email")
    password = form_data.get("password")

    db = get_db_connection()
    cursor = db.cursor()

    try:
        cursor.execute("SELECT id, password_hash FROM users WHERE email = %s", (email,))
        result = cursor.fetchone()

        if not result or not verify_password(password, result[1]):
            return app.jinja(request, "login.html", error="Incorrect email or password.", status_code=401)

        user_id = result[0]
        response = air.RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(
            "session",
            value=create_session_cookie(str(user_id), SECRET_KEY),
            httponly=True,
            samesite="Lax"
        )
        return response
    finally:
        cursor.close()
        db.close()

@app.post("/logout")
async def logout():
    response = air.RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("session")
    return response

@app.get("/dashboard")
async def dashboard(request: air.Request, session: str = Cookie(None)):
    if not session:
        return air.RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    db = get_db_connection()
    cursor = db.cursor()

    try:
        cursor.execute("SELECT id, name, qr_token FROM users LIMIT 1")
        user = cursor.fetchone()

        if not user:
            return air.RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

        user_id, user_name, qr_token = user

        cursor.execute("""
            SELECT u.name, u.bio, u.website, u.linkedin_url
            FROM dance_card_entries dce
            JOIN users u ON dce.scanner_id = u.id
            WHERE dce.owner_id = %s
            ORDER BY dce.created_at DESC
        """, (user_id,))
        connections = cursor.fetchall()

        qr_code_url = f"https://{DOMAIN}/s/{qr_token}"

        return app.jinja(request, "dashboard.html", user_name=user_name, qr_token=qr_token, qr_code_url=qr_code_url, connections=connections)
    finally:
        cursor.close()
        db.close()

@app.get("/s/{token}")
async def scan_step1(request: air.Request, token: str):
    db = get_db_connection()
    cursor = db.cursor()

    try:
        cursor.execute("SELECT id, name FROM users WHERE qr_token = %s", (token,))
        user = cursor.fetchone()

        if not user:
            return app.jinja(request, "error.html", message="Invalid share link. Try again?", status_code=404)

        owner_id, owner_name = user

        return app.jinja(request, "scan_step1.html", owner_name=owner_name, token=token)
    finally:
        cursor.close()
        db.close()

@app.post("/s/{token}")
async def scan_step2(request: air.Request, token: str):
    form_data = await request.form()
    email = form_data.get("email")
    name = form_data.get("name")
    bio = form_data.get("bio", "")
    website = form_data.get("website", "")
    linkedin_url = form_data.get("linkedin_url", "")
    password = form_data.get("password")

    db = get_db_connection()
    cursor = db.cursor()

    try:
        cursor.execute("SELECT id, name FROM users WHERE qr_token = %s", (token,))
        owner = cursor.fetchone()
        if not owner:
            raise HTTPException(status_code=404, detail="Invalid QR token")

        owner_id, owner_name = owner

        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        existing_user = cursor.fetchone()

        if existing_user:
            return app.jinja(request, "scan_step1.html", owner_name=owner_name, token=token, error="This email is already registered.", status_code=400)

        qr_token = secrets.token_urlsafe(6)[:6].upper()
        password_hash = hash_password(password)

        cursor.execute(
            "INSERT INTO users (email, name, bio, website, linkedin_url, qr_token, password_hash) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
            (email, name, bio, website, linkedin_url, qr_token, password_hash)
        )
        scanner_id = cursor.fetchone()[0]

        cursor.execute(
            "INSERT INTO dance_card_entries (owner_id, scanner_id) VALUES (%s, %s)",
            (owner_id, scanner_id)
        )
        db.commit()

        response = app.jinja(request, "scan_step3.html", owner_name=owner_name, token=token)
        response.set_cookie(
            "session",
            value=create_session_cookie(str(scanner_id), SECRET_KEY),
            httponly=True,
            samesite="Lax"
        )
        return response
    except Exception:
        db.rollback()
        return app.jinja(request, "scan_step1.html", error="Error processing signup.", status_code=500)
    finally:
        cursor.close()
        db.close()

@app.post("/s/{token}/add")
async def scan_step3(request: air.Request, token: str, session: str = Cookie(None)):
    if not session:
        return air.RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)

    db = get_db_connection()
    cursor = db.cursor()

    try:
        cursor.execute("SELECT id FROM users WHERE qr_token = %s", (token,))
        owner = cursor.fetchone()
        if not owner:
            raise HTTPException(status_code=404, detail="Invalid QR token")

        owner_id = owner[0]
        cursor.execute("SELECT id FROM users LIMIT 1")
        scanner = cursor.fetchone()
        scanner_id = scanner[0] if scanner else None

        if scanner_id:
            cursor.execute(
                "INSERT INTO dance_card_entries (owner_id, scanner_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (scanner_id, owner_id)
            )
            db.commit()

        return air.RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    finally:
        cursor.close()
        db.close()
