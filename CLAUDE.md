# Dance Card (PyCon Asia Networking App)

**Framework:** Air (Python web framework built on FastAPI)
**Database:** AirModel (async ORM) via Railway Postgres (`DATABASE_URL`)
**Deploy:** Railway

## Key Rules

1. **Use Air for all HTML routes** — `app.jinja(request, "template.html", **kwargs)` or Air tags
2. **For REST APIs** — mount a FastAPI app under `/api`: `app.mount("/api", api)`
3. **Use `DATABASE_URL`** — Air auto-connects asyncpg when set
4. **Import AirModel models AFTER `app = air.Air()`** — models register with `app.db` automatically
5. **Use int PKs, not UUID** — AirModel has a UUID bug; use `Optional[int]` with `AirField(default=None, primary_key=True)`. Let AirModel auto-generate via DB auto-increment; do NOT pass `id=uuid.uuid4()` in create calls
6. **All DB queries are async** — use `await Model.filter()`, `await Model.create()`, `await Model.get()`
7. **Keep main.py thin** — move business logic to `app/services.py`
8. **Run locally:** `./run.sh` (which runs `uv run air run`)

## Product Context

- **PRD:** `bridgerton_dance_card.md`
- **SDD:** `bridgerton_dance_card_sdd.md`
- **UX:** `bridgerton_dance_card_ux.md`

## Air Best Practices

1. **Use async/await properly** — Routes should be `async def` when they call `await` (e.g., `await request.form()`)
2. **Use type hints** — All function parameters and returns should have types for IDE autocomplete
3. **Use `Optional[]` not `|`** — Write `Optional[int]` instead of `int | None` for clarity
4. **Keep routes thin** — move business logic to `app/services.py`
5. **Int PKs auto-generated** — Let AirModel auto-increment; do NOT pass `id=...` in `Model.create()` calls
6. **Use AirModel for all DB queries** — fully async, no blocking I/O
7. **HMAC-signed sessions** — use `itsdangerous.URLSafeSerializer` for security; session cookie stores user_id as string, `int()` to decode
8. **Session management** — validate tokens in `get_user_id_from_session()`, never assume identity
9. **Error handling** — Use `HTTPException` from FastAPI for API errors, return templated error pages for HTML
10. **Template variables** — Pass all context via kwargs to `app.jinja()`, never use global state
11. **Form handling** — Use Pydantic models with AirForm for type-safe validation when possible
12. **Status codes** — Use `status.HTTP_303_SEE_OTHER` (303) for POST→GET redirects, `HTTP_302_FOUND` (302) for simple redirects

## Current Architecture

- **Database**: AirModel (async ORM) with asyncpg — fully async, no blocking I/O
- **Models** (`app/models.py`): User and DanceCardEntry with int auto-increment PKs
- **Services** (`app/services.py`): business logic (e.g., `get_user_connections()`)
- **Auth** (`app/auth.py`): HMAC-signed session cookies via `itsdangerous.URLSafeSerializer` (stores/decodes user_id as string)
- **Routes** (`main.py`): thin handlers that delegate to services/models
- **Templates** (`templates/`): Jinja2 — can mix with Air tags if needed
- **Auto-migration**: AirModel auto-creates tables on startup (via `app.db`); no explicit `create_tables()` call needed

## Framework Reference

- **Air AGENTS.md**: https://github.com/feldroy/Air/blob/main/AGENTS.md
- **AirModel README**: https://github.com/feldroy/AirModel#readme
- **AirModel AGENTS.md**: https://github.com/feldroy/AirModel/blob/main/AGENTS.md
