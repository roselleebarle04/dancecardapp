# Dance Card - Conference Networking App

## Problem Statement

At conferences, meeting great people is hard to follow up on:
- **"What was your name again?"** - you forget names
- **"Have I added you to LinkedIn yet?"** - contact info gets lost
- **"Where are you off to? Which talk?"** - no context saved
- **"Have you been to this great bar with good oldies music"** - but you didn't and forgot the name
- No frictionless way to track connections post-event

## Solution

A fun, QR code-based contact tracker for conference networking.

**Flow**: You generate a QR code → people scan it at the conference → you both optionally share your LinkedIn → you each get a cute list of your new connections in one place.

---

## MVP - Hackathon Scope

### For Dance Card Owner (You)
- Sign up with name + LinkedIn handle
- Generate a unique static QR code (links to your profile page)
- View your private dance card — a list of everyone who shared their info with you
- Design: Trendy, cute, fun aesthetic ✨

### For Scanners (People Meeting You)

**Step 1 — Share your info with them:**
- Scan QR code → see owner's profile (name + LinkedIn)
- Prompt: **"Share your LinkedIn with [Name]?"**
  - **No** → nothing saved, can scan again anytime
  - **Yes** → scanner's info added to owner's dance card ✓ → proceed to Step 2

**Step 2 — Add them to your own dance card (optional):**
- Prompt: **"Add [Name] to your dance card?"**
  - **No** → flow ends, owner still has scanner's info
  - **Yes** → scanner is prompted to sign up (name + LinkedIn handle, quick form)
    - If scanner already has an account → owner is added to their dance card ✓
    - If scanner is new → quick signup (name + LinkedIn) → owner added to their new dance card ✓

---

## Data Model

**User:**
- Name
- LinkedIn handle (used as unique identifier)
- QR token — 6-character alphanumeric, static, generated on signup (e.g. `xK9mP2`)

**QR Code URL format:**
```
dancecard.app/s/xK9mP2
```
- `/s/` = scan route, keeps URL short
- 6-char token = ~56 billion combinations, low-density QR code = easy to scan on a phone or printed badge
- Token never changes (no reset in MVP)

**Dance Card Entry:**
- Owner (whose dance card this appears in)
- Connection's name
- Connection's LinkedIn handle
- Timestamp

**Notes:**
- Dance card is private — only visible to the owner
- Same person can scan multiple times (no restrictions)
- No LinkedIn API — handles entered manually

---

## Tech Stack (MVP)
- **Framework**: AIR (FastAPI/Starlette-based, Python)
- **Database**: Supabase (hosted Postgres — real-time scans work across devices during demo)
- **Auth**: Simple session-based (no OAuth for MVP)
- **Hosting**: Railway (deploy from GitHub, ~5 min setup, custom domain support)

---

## Key Design Principles
- ✨ Fun and trendy UI (this is for-fun!)
- 🎯 Frictionless: scanners can share without a full account
- 🔄 Two-way: both people can end up on each other's dance cards
- 📱 Mobile-first (people scan at a conference)
- 🔐 Private dance cards (only you see yours)

---

## Out of Scope (Future Enhancements)
- LinkedIn OAuth login
- Messaging between users
- Post-conference integrations
- Export/sharing dance cards
- LinkedIn profile search/validation