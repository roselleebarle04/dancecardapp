import os
import secrets
from fastapi import FastAPI, Request, HTTPException, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
from app.db import init_db, get_db_connection
from app.auth import hash_password, verify_password, create_session_cookie
from app.qrcode_gen import generate_qr_code

load_dotenv()

app = FastAPI()

DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY")
DOMAIN = os.getenv("DOMAIN")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.on_event("startup")
async def startup():
    await init_db()

@app.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@app.post("/")
async def signup(request: Request):
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
            return templates.TemplateResponse("signup.html", {
                "request": request,
                "error": "This email is already registered. Try logging in?"
            }, status_code=400)

        qr_token = secrets.token_urlsafe(6)[:6].upper()
        password_hash = hash_password(password)

        cursor.execute(
            "INSERT INTO users (email, name, bio, website, linkedin_url, qr_token, password_hash) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
            (email, name, bio, website, linkedin_url, qr_token, password_hash)
        )
        user_id = cursor.fetchone()[0]
        db.commit()

        response = RedirectResponse(url="/dashboard", status_code=302)
        response.set_cookie(
            "session",
            value=create_session_cookie(str(user_id), SECRET_KEY),
            httponly=True,
            samesite="Lax"
        )
        return response
    except Exception as e:
        db.rollback()
        return templates.TemplateResponse("signup.html", {
            "request": request,
            "error": "Error creating account. Please try again."
        }, status_code=500)
    finally:
        cursor.close()
        db.close()

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request):
    form_data = await request.form()
    email = form_data.get("email")
    password = form_data.get("password")

    db = get_db_connection()
    cursor = db.cursor()

    try:
        cursor.execute("SELECT id, password_hash FROM users WHERE email = %s", (email,))
        result = cursor.fetchone()

        if not result or not verify_password(password, result[1]):
            return templates.TemplateResponse("login.html", {
                "request": request,
                "error": "Incorrect email or password."
            }, status_code=401)

        user_id = result[0]
        response = RedirectResponse(url="/dashboard", status_code=302)
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
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("session")
    return response

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, session: str = Cookie(None)):
    if not session:
        return RedirectResponse(url="/login", status_code=302)

    db = get_db_connection()
    cursor = db.cursor()

    try:
        cursor.execute("SELECT id, name, qr_token FROM users LIMIT 1")
        user = cursor.fetchone()

        if not user:
            return RedirectResponse(url="/login", status_code=302)

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

        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "user_name": user_name,
            "qr_token": qr_token,
            "qr_code_url": qr_code_url,
            "connections": connections
        })
    finally:
        cursor.close()
        db.close()

@app.get("/s/{token}", response_class=HTMLResponse)
async def scan_step1(request: Request, token: str):
    db = get_db_connection()
    cursor = db.cursor()

    try:
        cursor.execute("SELECT id, name FROM users WHERE qr_token = %s", (token,))
        user = cursor.fetchone()

        if not user:
            return templates.TemplateResponse("error.html", {
                "request": request,
                "message": "Invalid share link. Try again?"
            }, status_code=404)

        owner_id, owner_name = user

        return templates.TemplateResponse("scan_step1.html", {
            "request": request,
            "owner_name": owner_name,
            "token": token
        })
    finally:
        cursor.close()
        db.close()

@app.post("/s/{token}")
async def scan_step2(request: Request, token: str):
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
            return templates.TemplateResponse("scan_step1.html", {
                "request": request,
                "owner_name": owner_name,
                "token": token,
                "error": "This email is already registered."
            }, status_code=400)

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

        response = templates.TemplateResponse("scan_step3.html", {
            "request": request,
            "owner_name": owner_name,
            "token": token
        })
        response.set_cookie(
            "session",
            value=create_session_cookie(str(scanner_id), SECRET_KEY),
            httponly=True,
            samesite="Lax"
        )
        return response
    except Exception as e:
        db.rollback()
        return templates.TemplateResponse("scan_step1.html", {
            "request": request,
            "error": "Error processing signup."
        }, status_code=500)
    finally:
        cursor.close()
        db.close()

@app.post("/s/{token}/add")
async def scan_step3(request: Request, token: str, session: str = Cookie(None)):
    if not session:
        return RedirectResponse(url="/", status_code=302)

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

        return RedirectResponse(url="/dashboard", status_code=302)
    finally:
        cursor.close()
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
