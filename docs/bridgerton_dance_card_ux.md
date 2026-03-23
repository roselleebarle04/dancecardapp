# Dance Card: Product Requirements, System Design, and UX Spec

---

# System Design Document (SDD)

## 1. System Overview

**Dance Card** is a mobile-first networking web app that lets conference/event attendees exchange contact info via QR codes. Users create a "dance card" profile, share their QR code with others, and build a list of connections.

- **Architecture:** AIR (FastAPI/Starlette) → Supabase (Postgres) → Railway hosting
- **Deployment:** Railway (Nixpacks, Hypercorn)
- **Database:** Postgres (managed via Supabase)
- **Session management:** Signed cookies (Starlette SessionMiddleware)
- **Password hashing:** bcrypt
- **QR code generation:** `qrcode` Python library

## 2. Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Backend** | AIR (FastAPI/Starlette) | Web framework, routing, middleware |
| **ASGI Server** | Hypercorn | Production server on Railway |
| **Database** | Supabase (Postgres) | User storage, connection tracking |
| **Auth** | bcrypt + signed cookies | Password hashing, session storage |
| **QR codes** | `qrcode` library | Generate QR images (inline base64 PNG) |
| **Hosting** | Railway | Deployment platform with Nixpacks |

## 3. Pages & Routes

| Route | Method | Description | Auth required |
|-------|--------|-------------|-----------------|
| `/` | GET | Landing + signup form | No |
| `/` | POST | Create user + session | No |
| `/login` | GET | Login form | No |
| `/login` | POST | Authenticate user | No |
| `/logout` | POST | Clear session | Yes |
| `/dashboard` | GET | Owner's QR code + connection list | Yes |
| `/s/{token}` | GET | Scan page (Step 1: profile + share prompt) | No |
| `/s/{token}` | POST | Complete identity form (Step 2) | No |
| `/s/{token}/add` | POST | Add connection to scanner's card (Step 3) | No |

## 4. Database Schema

### users table
```sql
id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
email           TEXT NOT NULL UNIQUE
name            TEXT NOT NULL
bio             TEXT
website         TEXT
linkedin_url    TEXT
qr_token        CHAR(6) NOT NULL UNIQUE
password_hash   TEXT NOT NULL
created_at      TIMESTAMP DEFAULT now()
updated_at      TIMESTAMP DEFAULT now()
```

### dance_card_entries table
```sql
id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
owner_id        UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE
scanner_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE
created_at      TIMESTAMP DEFAULT now()
UNIQUE(owner_id, scanner_id)  -- prevent duplicate entries
```

## 5. Key Flows

### Signup Flow
1. GET `/` → show signup form
2. POST `/` with email, name, bio (optional), website (optional), LinkedIn (optional), password
3. Generate 6-char alphanumeric `qr_token`
4. Hash password with bcrypt
5. Create user in Supabase
6. Set signed session cookie
7. Redirect to `/dashboard`

**Error:** Duplicate email → show inline error, keep form filled (except password)

### Login Flow
1. GET `/login` → show login form
2. POST `/login` with email + password
3. Query user by email, verify password hash
4. Set signed session cookie
5. Redirect to `/dashboard`

**Error:** Bad credentials → show error, clear password field only

### Dashboard
1. GET `/dashboard` → verify session cookie, redirect to `/login` if missing
2. Render user's QR code image pointing to `/s/{qr_token}`
3. Fetch all dance_card_entries where owner_id = current user
4. Display entries sorted by most recent first
5. Show name, bio, website, LinkedIn for each

### Scan Flow (Public, 3 steps)

**Step 1:** GET `/s/{token}`
- Lookup user by `qr_token` (owner)
- Display owner's name, "Share your info with [Name]?" prompt
- Buttons: "No" | "Yes"
- "No" → show "Thanks for stopping by!", redirect to `/` after 2s
- "Yes" → proceed to Step 2

**Step 2:** POST `/s/{token}` (if not logged in)
- If scanner is already logged in → skip to Step 3
- If not logged in → show identity form (email, name, bio, website, LinkedIn, password)
- Create new user (or find existing), set session cookie
- Create `dance_card_entry` (owner_id=owner, scanner_id=scanner)
- Proceed to Step 3

**Step 3:** POST `/s/{token}/add` (reverse connection)
- Display owner's profile (name, bio, website, LinkedIn)
- Buttons: "No" | "Yes"
- "No" → show "Thanks for connecting!", redirect to `/dashboard` (or `/` if not logged in)
- "Yes" → create dance_card_entry (owner_id=scanner, scanner_id=owner)
- Redirect to `/dashboard` with success message "[Name] added to your dance card!"

## 6. API Endpoints (Detailed)

### POST `/`
**Request body:**
```json
{
  "email": "user@example.com",
  "name": "Jane Doe",
  "bio": "Engineer at Acme",
  "website": "https://example.com",
  "linkedin_url": "https://linkedin.com/in/jane-doe",
  "password": "securepassword"
}
```
**Response:** 302 redirect to `/dashboard` on success, or 400 with error message

### POST `/login`
**Request body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword"
}
```
**Response:** 302 redirect to `/dashboard` on success, or 401 with error message

### POST `/logout`
**Response:** 302 redirect to `/`, session cleared

### GET `/dashboard`
**Response:** 200 with HTML page (user's profile, QR code, connection list)

### GET `/s/{token}`
**Response:** 200 with Step 1 form (owner profile + "Share your info?" prompt)

### POST `/s/{token}`
**Request body:**
```json
{
  "email": "scanner@example.com",
  "name": "John Doe",
  "bio": "Designer at Acme",
  "website": "https://john.example.com",
  "linkedin_url": "https://linkedin.com/in/john-doe",
  "password": "securepassword"
}
```
**Response:** 200 with Step 3 form (owner profile + "Add to your dance card?" prompt) or 400 on error

### POST `/s/{token}/add`
**Response:** 302 redirect to `/dashboard` with success toast

## 7. Authentication

- **Method:** Signed session cookies (Starlette SessionMiddleware)
- **Password hashing:** bcrypt (minimum 12 rounds)
- **Session lifetime:** 30 days (configurable)
- **CSRF protection:** Enabled (Starlette default)

## 8. Error Handling

| Error | Status | Message | UI Action |
|-------|--------|---------|-----------|
| Duplicate email | 400 | "This email is already registered. Try logging in?" | Show inline, keep form (except password) |
| Bad credentials | 401 | "Incorrect email or password." | Show error, clear password field |
| Invalid QR token | 404 | "Invalid share link. Try again?" | Show on page, link to home |
| Session expired | 302 | (redirect to login) | Redirect to `/login` |
| Server error | 500 | "Something went wrong. Try again." | Show toast, allow retry |

## 9. Security Considerations

- **HTTPS only** — enforced by Railway via domain SSL
- **CSRF protection** — Starlette middleware
- **SQL injection** — Supabase SDK handles parameterized queries
- **XSS prevention** — Template escaping (Starlette Jinja2)
- **Password requirements** — Minimum 8 characters (enforced client-side + server-side validation)
- **Rate limiting** — Not implemented in MVP (add later if needed)
- **CORS** — Same-origin only (no external API calls)
- **Data privacy** — No data shared outside Supabase; terms & privacy policy to be added post-launch

## 10. QR Code Generation

- Use `qrcode` Python library
- Generate on-demand when rendering `/dashboard`
- Output as base64 PNG (inline in HTML, no file storage)
- QR code points to `https://dancecard.app/s/{qr_token}`
- Size: 280x280px (fits in dialog box panel)

## 11. Deployment & Infrastructure

### Railway Setup

**Prerequisites:**
- Railway account + project linked to GitHub repo
- AIR project with `main.py` containing the app instance

**Installation:**

1. Add Hypercorn to dependencies:
   ```bash
   uv add hypercorn
   ```

2. Create `railway.json` in project root:
   ```json
   {
     "$schema": "https://railway.app/railway.schema.json",
     "build": {
       "builder": "NIXPACKS"
     },
     "deploy": {
       "startCommand": "uv run hypercorn main:app --bind \"[::]:$PORT\""
     }
   }
   ```

3. Commit `uv.lock` to version control (do not exclude)

4. Push to main branch → Railway auto-deploys via Nixpacks

**Environment Variables (set in Railway dashboard):**
- `DATABASE_URL` — Supabase Postgres connection string
- `SECRET_KEY` — Session signing key (generate with `secrets.token_urlsafe(32)`)
- `ENVIRONMENT` — `production` or `staging`
- `DOMAIN` — `dancecard.app` (for QR code generation)

**Build Process:**
- Railway detects Python project via Nixpacks
- Installs uv, downloads dependencies from `uv.lock`
- Runs health checks on startup

**Port Binding:**
- Hypercorn binds to `$PORT` environment variable (Railway provides this)
- Start command: `uv run hypercorn main:app --bind "[::]:$PORT"`

### Supabase Integration

**Setup:**
1. Create Supabase project (database, auth, managed Postgres)
2. Copy `DATABASE_URL` from project settings
3. Run migrations via `psql` CLI or Supabase SQL editor

**Connection:**
- Use `psycopg2` or `supabase-py` client
- Connection pooling: Supabase includes built-in pooler
- Backup: Supabase handles daily automated backups

## 12. Monitoring & Logging

**Logging:**
- Log all authentication attempts (success/failure)
- Log all dance_card_entry creations
- Log errors to stderr (Railway captures)

**Monitoring (post-MVP):**
- User signups per day
- QR scan rate
- Connection creation rate
- Error rate by endpoint
- Database query latency

**Alerts (post-MVP):**
- High error rate (>5% of requests)
- Database down
- Deployment failure

---

# UX Specification

## Page 1: Landing / Signup (`/`)

**Header:**
- Logo/title "Dance Card"
- Link to `/login` ("Already have an account?")

**Form Fields:**
- Email (text input)
- Name (text input)
- Bio (optional textarea, placeholder "A sentence about you — role, company, what you're working on...")
- Website (optional text input, placeholder "https://...")
- LinkedIn URL (optional text input, placeholder "https://linkedin.com/in/...")
- Password (password input)
- Submit button: "Create Dance Card"

**Behaviors:**
- On submit → POST to `/` with form data
- Success → redirect to `/dashboard`
- Error (e.g., duplicate email) → show error message inline, keep form filled

---

## Page 2: Login (`/login`)

**Header:**
- Logo/title "Dance Card"
- Link to `/` ("Don't have an account?")

**Form Fields:**
- Email (text input)
- Password (password input)
- Submit button: "Sign In"

**Behaviors:**
- On submit → POST to `/login` with credentials
- Success → redirect to `/dashboard`
- Error (bad credentials) → show error message, clear password field only

---

## Page 3: Dashboard (`/dashboard`)

**Protected route** — if not logged in, redirect to `/login`

**Header:**
- User's name (e.g., "Jane's Dance Card")
- Logout button

**QR Code Section:**
- Headline: "Share your code"
- Display QR code image (points to `/s/{qr_token}`)
- Copy button: copies `dancecard.app/s/{qr_token}` to clipboard

**Dance Card List:**
- Headline: "Your connections"
- If empty: "No connections yet. Scan someone's code or share yours!"
- If populated: List of people, sorted by most recent first
  - Each entry shows: name, bio (if set), website link (if set), LinkedIn link (if set)

**Behaviors:**
- QR code regenerates on page load (always current)
- Copy button shows "Copied!" confirmation briefly
- Clicking on a person's LinkedIn link opens in new tab

---

## Page 4: Scan (`/s/{token}`)

**Public page** — no auth required

### Step 1: Owner Profile + Share Prompt

**Display:**
- Owner's name (from QR token lookup)
- Headline: "Share your info with [Name]?"
- Two buttons: "No" | "Yes"

**Behaviors:**
- "No" → show "Thanks for stopping by!" and redirect to `/` after 2 seconds
- "Yes" → proceed to Step 2

### Step 2: Scanner Identity

**If scanner is logged in:**
- Skip to Step 3

**If scanner is NOT logged in:**
- Show form: Email + Name + Bio (optional) + Website (optional) + LinkedIn (optional) + Password
- Headline: "What's your email?"
- Submit button: "Continue"
- Error handling: duplicate email → show error, keep name field

**Behaviors:**
- On submit → create user + create dance_card_entry (owner_id={qr_owner}, scanner_id={new_user})
- On success → set session cookie + proceed to Step 3

### Step 3: Add to Your Dance Card

**Display:**
- Headline: "Add [Owner Name] to your dance card?"
- Owner's bio (if set)
- Owner's website link (if set, clickable, opens in new tab)
- Owner's LinkedIn (if set, clickable, opens in new tab)
- Two buttons: "No" | "Yes"

**Behaviors:**
- "No" → show "Thanks for connecting!" and redirect to `/dashboard` (or `/` if not logged in)
- "Yes" → POST to create dance_card_entry (owner_id={scanner}, scanner_id={qr_owner})
  - Redirect to `/dashboard` with success message: "[Name] added to your dance card!"

---

## State & Navigation Flow

```
Landing (/)
  → Signup success
    → Dashboard (/dashboard)

Login (/login)
  → Login success
    → Dashboard (/dashboard)

Dashboard (/dashboard)
  → Share QR code link
    → /s/{token} (Step 1)

Scan (/s/{token})
  → Step 1: "Share your info with [Name]?"
    → No: Redirect to /
    → Yes: Step 2

  → Step 2: Identity (if not logged in)
    → Form: Email + Name + LinkedIn (optional) + Password
    → Success: Step 3
    → Error: Show error, retry

  → Step 3: "Add to your dance card?"
    → No: Show thanks, redirect to / or /dashboard
    → Yes: Create entry, redirect to /dashboard with success toast
```

---

## Visual Style

This section describes the cozy, Stardew Valley-inspired aesthetic built with Sprout Lands UI Pack assets and warm solid colors. No background tilesets yet — focus is on panels, buttons, and typography.

### Assets Used from Sprout Lands UI Pack

| Asset | File | Use |
|-------|------|-----|
| Font | `fonts/pixelFont-7-8x14-sproutLands.ttf` | All headings and labels via `@font-face` |
| Panel | `Sprite sheets/Dialouge UI/Premade dialog box big.png` | QR code panel, form containers, connection cards — via CSS `border-image` (9-slice) |
| Panel (medium) | `Sprite sheets/Dialouge UI/Premade dialog box medium.png` | Smaller cards / toasts |
| Buttons | `Sprite sheets/buttons/Square Buttons 26x26.png` | Yes/No buttons, submit buttons — via `background-image` sprite |

### Color Palette

| Role | Hex | Notes |
|------|-----|-------|
| Page background | `#e8d5b0` | Warm parchment, matches pack palette |
| Panel fill | `#f0e6d3` | Cream interior (behind border-image) |
| Heading text | `#5c3d1e` | Dark brown, readable on cream |
| Body text | `#3a2a1a` | Near-black brown |
| Primary button | `#6aaa5a` | Soft green (from pack's button tones) |
| Danger / error | `#c0392b` | Red |
| Success toast | `#5aaa6a` | Green |

### Implementation Notes

- **Font loading:** `@font-face { font-family: 'SproutLands'; src: url('/static/fonts/pixelFont-7-8x14-sproutLands.ttf'); }`
- **Panel borders:** `border-image: url('/static/ui/dialog-box-big.png') 6 fill / 6px stretch` (exact slice values to be tuned when building — the dialog box has ~6px borders)
- **Buttons:** Use CSS `background-image` with sprite offset for normal/hover/pressed states from `Square Buttons 26x26.png`
- **Pixel rendering:** Apply `image-rendering: pixelated` on all sprite-based elements
- **Corners:** No `border-radius` anywhere — pixel art is all sharp corners

### UI Elements

| Component | Style |
|-----------|-------|
| Page background | Solid `#e8d5b0` |
| Panels / forms | Sprout Lands dialog box `border-image`, cream fill `#f0e6d3` |
| Headings | SproutLands font, dark brown `#5c3d1e` |
| Body text | System font (SproutLands too small for body), `#3a2a1a` |
| Buttons | Sprout Lands square button sprite, no border-radius |
| Form inputs | Solid `#f0e6d3` bg, `2px solid #7a5230` border, no border-radius |
| Error messages | Red `#c0392b` text inline below field |
| Success toast | Medium dialog box panel, top-center, 3s auto-dismiss |
| Links | Dark brown, underline on hover, new tab for external |
| QR code | Inside dialog box panel, 280x280px, `image-rendering: pixelated` |

### Deferred

- Pixel art tileset background — add later once core app is working

---

## Copy & Messaging

| Context | Message |
|---------|---------|
| Signup success | None — redirect immediately |
| Login success | None — redirect immediately |
| Duplicate email | "This email is already registered. Try logging in?" |
| Bad credentials | "Incorrect email or password." |
| Scan "No" | "Thanks for stopping by!" |
| Scan "Yes" (no entry) | Entry created, redirect |
| Scan "Yes" (duplicate) | Prevent duplicate — either skip or show "You're already connected!" |
| Dashboard empty | "No connections yet. Scan someone's code or share yours!" |
| Copy QR link | "Copied!" (2s toast) |

