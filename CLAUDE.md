# Dance Card (PyCon Asia Networking App)

**Framework:** Air (Python web framework built on FastAPI)
**Database:** AirModel (async ORM) via Railway Postgres (`DATABASE_URL`)
**Deploy:** Railway

## Key Rules

1. **Use Air for all HTML routes** — `app.jinja(request, "template.html", **kwargs)` or Air tags
2. **For REST APIs** — mount a FastAPI app under `/api`: `app.mount("/api", api)`
3. **Use `DATABASE_URL`** — Air auto-connects asyncpg when set
4. **All DB queries are async** — use `await Model.filter()`, `await Model.create()`, `await Model.get()`
5. **Keep main.py thin** — move business logic to `app/services.py`
6. **Run locally:** `./run.sh` (which runs `uv run air run`)

## Product Context

- **PRD:** `bridgerton_dance_card.md`
- **SDD:** `bridgerton_dance_card_sdd.md`
- **UX:** `bridgerton_dance_card_ux.md`

## Air Best Practices

1. **Use async/await properly** — Routes should be `async def` when they call `await` (e.g., `await request.form()`)
2. **Use type hints** — All function parameters and returns should have types for IDE autocomplete
3. **Use `Optional[]` not `|`** — Write `Optional[UUID]` instead of `UUID | None` for clarity
4. **Keep routes thin** — move business logic to `app/services.py`
4. **Use AirModel for all DB queries** — fully async, no blocking I/O
5. **HMAC-signed sessions** — use `itsdangerous.URLSafeSerializer` for security
6. **Session management** — validate tokens in `get_user_id_from_session()`, never assume identity
7. **Error handling** — Use `HTTPException` from FastAPI for API errors, return templated error pages for HTML
8. **Template variables** — Pass all context via kwargs to `app.jinja()`, never use global state
9. **Form handling** — Use Pydantic models with AirForm for type-safe validation when possible
10. **Status codes** — Use `status.HTTP_303_SEE_OTHER` (303) for POST→GET redirects, `HTTP_302_FOUND` (302) for simple redirects

## Current Architecture

- **Database**: AirModel (async ORM) with asyncpg — fully async, no blocking I/O
- **Models** (`app/models.py`): User and DanceCardEntry with UUID PKs
- **Services** (`app/services.py`): business logic (e.g., `get_user_connections()`)
- **Auth** (`app/auth.py`): HMAC-signed session cookies via `itsdangerous.URLSafeSerializer`
- **Routes** (`main.py`): thin handlers that delegate to services/models
- **Templates** (`templates/`): Jinja2 — can mix with Air tags if needed
- **Auto-migration**: AirModel creates/migrates tables on startup

## Framework Reference

- **Air AGENTS.md**: https://github.com/feldroy/Air/blob/main/AGENTS.md
- **AirModel AGENTS.md**: https://github.com/feldroy/AirModel/blob/main/AGENTS.md
