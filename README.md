# Embeddable Widget & Lead-Capture Platform

FlyRank Backend Track capstone — a platform that lets a customer define a widget, embed it on any
website with one `<script>` tag, and safely receive, validate, spam-filter, enrich, and dashboard
whatever the public internet submits back.

**Status:** 🚧 Phase 2 — the hardened public submission path is built. Widget management,
delivery, and the owner dashboard land in Phase 3.

## Stack
Python · FastAPI · SQLAlchemy · PostgreSQL (Docker) or SQLite for quick local dev · slowapi

## What's built so far (Phase 2)
`POST /submissions` — the public endpoint a customer's website calls when a visitor submits
a widget's form:
- CORS-enabled (any origin), preflight handled automatically
- input validated (field count, field length, request size) → clean 4xx on anything malformed or oversized
- rate limited per IP → 429 on a burst, service keeps serving other traffic
- honeypot spam control → spam is stored and flagged, response still looks like success
- IP → geo enrichment with a two-provider fallback chain, degrades to "no geo" if both are down
- confirmation side effect (stubbed as a log line) — its failure can never break the submission

## Quick start (SQLite, no Docker)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python seed.py              # creates the DB + one demo widget, prints a ready-to-run curl command
uvicorn app.main:app --reload
```
Then, from a second terminal, run the curl command `seed.py` printed, or:
```bash
curl -i -X POST http://localhost:8000/submissions \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:5500" \
  -d '{"widget_id": "00000000-0000-0000-0000-0000000000aa", "fields": {"email": "visitor@example.com"}}'
```

## Quick start (Postgres via Docker)
```bash
cp .env.example .env
docker compose up --build
# in another terminal, one-off seed against the running container's DB:
docker compose exec app python seed.py
```

## Run the tests
```bash
pytest -v
```
Covers validation (4xx/413), CORS + preflight, rate limiting (429), the honeypot spam control,
the geo provider fallback chain (both branches), and the notify-failure-doesn't-break-storage case.

## Proving the fallback chain / failure modes yourself
All controlled through `.env`, no code changes needed:
- `MOCK_PROVIDER_A_UP=false` → next submission is enriched by provider B instead of A
- `MOCK_PROVIDER_A_UP=false` and `MOCK_PROVIDER_B_UP=false` → submission still stored, no geo
- `FORCE_NOTIFY_FAIL=true` → confirmation side effect throws; submission is still stored and returns 201

## Docs
- [`DESIGN.md`](./DESIGN.md) — problem, data model, API surface, architecture, non-goal
- [`EVIDENCE.md`](./EVIDENCE.md) — proof per requirement (paste real output here as you test)
- [`BUILDLOG.md`](./BUILDLOG.md) — honest AI-usage log
- `capstone.yaml` — evaluator manifest (added in Phase 3)

## Limitations (honest, as of Phase 2)
- No auth/widget-management API yet — `seed.py` inserts one fixed demo widget so the
  submission path can be tested end-to-end. Phase 3 adds real owner accounts and CRUD.
- Rate limiting is per-process in-memory (via slowapi's default backend) — fine for one
  instance, would need a shared backend (e.g. Redis) behind multiple app instances.
- Geo enrichment defaults to `GEO_MODE=mock` for deterministic, offline-safe testing;
  `GEO_MODE=live` calls the real free providers but was only spot-checked manually, not
  covered by the automated tests (mocking is what the brief asks for there).
