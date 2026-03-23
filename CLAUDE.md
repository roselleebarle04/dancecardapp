# Dance Card (PyCon Asia Networking App)

**Framework:** Air (Python web framework built on FastAPI)
**Database:** Railway Postgres via `PSYCOPG_URL`
**Deploy:** Railway

## Key Rules

1. **Use Air for all HTML routes** — `app.jinja(request, "template.html", **kwargs)` or Air tags
2. **For REST APIs** — mount a FastAPI app under `/api`: `app.mount("/api", api)`
3. **Use `PSYCOPG_URL`** — not `DATABASE_URL` (avoids Air auto-asyncpg)
4. **Run locally:** `./run.sh` (which runs `uv run air run`)

## Product Context

- **PRD:** `bridgerton_dance_card.md`
- **SDD:** `bridgerton_dance_card_sdd.md`
- **UX:** `bridgerton_dance_card_ux.md`

## Framework Reference

Complete Air docs: `.claude/AIR_WEB_FRAMEWORK.md`
