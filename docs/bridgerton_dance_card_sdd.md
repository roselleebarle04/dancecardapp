# Dance Card SDD — Bridgerton Hackathon Networking App

## System Overview

The Dance Card is a mobile-first web application designed for conference networking. It allows attendees to connect by scanning QR codes and building a "dance card" (a list of connections made).

**Architecture:**
- **Backend:** AIR framework (FastAPI/Starlette)
- **Database:** Supabase (Postgres)
- **Hosting:** Railway
- **Frontend:** Mobile-first web app (no native app needed — QR scan opens browser)

## Pages & Routes

| Route | Description | Auth Required |
|-------|-------------|---|
| `/` | Landing + signup form | No |
| `/login` | Login form | No |
| `/dashboard` | Owner's QR code + dance card list | Yes |
| `/s/{token}` | Scan page — shows owner profile + share prompt | No |

## Database Schema (Supabase/Postgres)

### users table
```sql
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  bio TEXT,
  website TEXT,
  linkedin TEXT,
  qr_token CHAR(6) NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT now()
);
```

### dance_card_entries table
```sql
CREATE TABLE dance_card_entries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  scanner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at TIMESTAMP DEFAULT now(),
  UNIQUE(owner_id, scanner_id)
);
```

**Explanation:**
- `owner_id` — whose dance card this entry lives in
- `scanner_id` — who was added (must be a user)
- UNIQUE constraint prevents duplicate entries

## Key Flows

### Signup Flow

1. User submits POST `/` with email + name + bio (optional) + website (optional) + linkedin (optional) + password
2. Validate email is unique
3. Generate 6-character alphanumeric `qr_token` (ensure uniqueness)
4. Hash password with bcrypt
5. Create user record in Supabase
6. Set session cookie
7. Redirect to `/dashboard`

### Login Flow

1. User submits POST `/login` with email + password
2. Look up user by email
3. Verify password hash against stored hash
4. Set session cookie
5. Redirect to `/dashboard`

### Dashboard Flow

1. GET `/dashboard` — verify session cookie
2. Retrieve current user
3. Render QR code image pointing to `dancecard.app/s/{qr_token}`
4. Query and list all `dance_card_entries` where `owner_id = current_user.id`
5. Display list of people who scanned the QR code

### Scan Flow (`/s/{token}`)

1. GET `/s/{token}` — look up user by `qr_token`
2. If not found → 404
3. Display **Step 1 prompt:** "Share your LinkedIn with [Name]?"
   - **No** → done, redirect to landing
   - **Yes** → proceed to Step 2

4. **Step 2:** Verify scanner identity
   - If already logged in → proceed with current user as scanner
   - If not logged in → show quick signup/login form (email + name + linkedin (optional) + password)
     - On successful signup/login → set session, proceed
   - POST to create `dance_card_entry(owner_id={qr_token_owner}, scanner_id={current_user})`

5. **Step 3 prompt:** "Add [Name] to your dance card?"
   - **No** → done
   - **Yes** → POST to create `dance_card_entry(owner_id={current_user}, scanner_id={qr_token_owner})`
   - Redirect to scanner's `/dashboard`

## QR Code Generation

- Use Python `qrcode` library
- Generate dynamically on `/dashboard` render
- Point QR code to `dancecard.app/s/{qr_token}`
- Render as inline base64-encoded PNG (no file storage needed)

**Example:**
```python
import qrcode
from io import BytesIO
import base64

qr = qrcode.QRCode(version=1, box_size=10, border=5)
qr.add_data(f"https://dancecard.app/s/{user.qr_token}")
qr.make(fit=True)
img = qr.make_image(fill_color="black", back_color="white")

# Convert to base64 for inline <img src="data:image/png;base64,...">
buffer = BytesIO()
img.save(buffer, format='PNG')
img_base64 = base64.b64encode(buffer.getvalue()).decode()
```

## Authentication

- **Password Hashing:** bcrypt (recommended 12 rounds)
- **Session Management:** Starlette SessionMiddleware with signed cookies
- **Scope:** No OAuth for MVP — username/password only
- **Session Expiry:** 30 days (or as desired)

## Tech Stack

| Layer | Technology |
|-------|---|
| Framework | FastAPI/Starlette (AIR) |
| Database | Supabase (managed Postgres) |
| ORM | SQLAlchemy or raw psycopg2 |
| Auth | bcrypt, Starlette SessionMiddleware |
| QR Generation | `qrcode` library |
| Hosting | Railway |

## Verification Checklist

- [ ] Sign up with email + name + password (linkedin optional)
- [ ] Dashboard displays QR code
- [ ] QR code links to `/s/{token}` correctly
- [ ] Visit `/s/{token}` on mobile — see owner's profile
- [ ] Submit "share your info" form without being logged in
- [ ] Quick signup/login form appears with email field
- [ ] After signup/login, entry appears in owner's dance card
- [ ] Verify two-way entries: when scanner signs up, owner appears in scanner's dashboard
- [ ] Test duplicate entry prevention (scanning same QR twice doesn't create duplicate)
- [ ] Test duplicate email prevention during signup
- [ ] Password hashing works (can't log in with wrong password)
- [ ] Session cookie persists across page reloads
- [ ] Session expires after 30 days (or configured duration)

## Deployment Notes

- Configure Railway environment variables: `DATABASE_URL`, `SECRET_KEY`, `DOMAIN`
- Set up Supabase connection pooling if expected load is high
- Enable HTTPS in production (Railway handles this)
- Store SECRET_KEY securely in Railway secrets (for session signing)
