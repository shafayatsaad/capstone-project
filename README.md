# FlyRank Embeddable Widget & Lead-Capture Platform

A small, production-minded lead capture service: owners create tenant-isolated widgets, paste one script tag into a customer website, and view submissions and geo analytics in an authenticated dashboard API. The public submission path validates untrusted input, handles cross-origin browser requests, limits bursts, silently drops honeypot spam, enriches locations with a fallback chain, and queues a retryable notification after storing.

## Architecture

```text
Owner browser -- bearer JWT --> Auth + Widget API -- owner_id scope --> PostgreSQL / SQLite
       |                            |                                |
       +-- Embed snippet ----------+                                +-- Dashboard API
Customer site (port 5500) -- GET widget.js (immutable) --> Public Delivery
       |                           +-- GET /widgets/{id}/config (60 s cache)
       +-- POST /submissions (CORS, schema + byte limits, IP limiter, honeypot)
                                     |-- Provider A -> Provider B -> no geo
                                     +-- DB transaction: submission + notification outbox
                                                           +-- Background retry worker -> notification log
```

Routers handle HTTP, Pydantic schemas validate boundaries, services implement submission/enrichment/notification rules, repositories persist records, and every owner-facing widget/submission query is scoped through `owner_id`.

## Run locally

Requirements: Python 3.11+ and Docker Desktop for the Postgres path. For the SQLite path, Docker is optional.

### SQLite

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
alembic upgrade head
python seed.py
uvicorn app.main:app --reload
```

Open API documentation at <http://localhost:8000/docs>. Serve the second-origin demo in another terminal:

```powershell
python -m http.server 5500 --directory static/demo
```

Open <http://localhost:5500/> to see the seeded widget. It is served from a different port than the API, so the browser exercises CORS and the real embed script.

### PostgreSQL via Docker Compose

```powershell
Copy-Item .env.example .env
docker compose up --build
```

The app container runs `alembic upgrade head` before starting. In another terminal, seed the demo owner and widget:

```powershell
docker compose exec app python seed.py
```

The database is exposed on localhost:5432 for local inspection. Change the sample credentials before using this outside a local demo.

## First owner and widget

Register an owner, save the access token, then create a widget and retrieve its embed line:

```powershell
$owner = Invoke-RestMethod -Method Post http://localhost:8000/auth/register `
  -ContentType 'application/json' `
  -Body '{"email":"you@example.com","password":"a-long-demo-password"}'
$headers = @{ Authorization = "Bearer $($owner.access_token)" }
$widget = Invoke-RestMethod -Method Post http://localhost:8000/widgets `
  -Headers $headers -ContentType 'application/json' `
  -Body '{"title":"Get product updates","description":"A short signup form","fields":[{"name":"email","label":"Email","type":"email","required":true}],"button_text":"Join the list"}'
Invoke-RestMethod "http://localhost:8000/widgets/$($widget.id)/embed" -Headers $headers
```

Paste the returned script into a page on a different origin. Or open the demo with `?widget_id=<id>`.

## API overview

| Method | Path | Access | Purpose |
|---|---|---|---|
| `POST` | `/auth/register`, `/auth/login` | Public | Create account or issue a signed bearer token |
| `POST/GET` | `/widgets` | Owner JWT | Create and list only the caller's widgets |
| `GET/PUT/DELETE` | `/widgets/{id}` | Owner JWT | Read, update, or delete an owned widget; updates increment `version` |
| `GET` | `/widgets/{id}/embed` | Owner JWT | Return the current versioned `<script>` snippet |
| `GET` | `/widget.js?id={id}&v={version}` | Public | Deliver embed bundle with one-year immutable cache |
| `GET` | `/widgets/{id}/config` | Public | Deliver small config with a 60-second cache |
| `POST` | `/submissions` | Public | Validate, rate-limit, enrich, store, and queue notification |
| `GET` | `/dashboard/submissions` | Owner JWT | Paginated, owner-scoped submissions; spam is excluded |
| `GET` | `/dashboard/stats` | Owner JWT | Counts per widget and geo country for a selected period |
| `GET` | `/health` | Public | Liveness check |

Submission body: `{"widget_id":"...","fields":{"email":"visitor@example.com"},"hp_field":""}`. An optional `Idempotency-Key` header makes retries return the original submission rather than creating another row. Payload byte, field-count, and field-size limits are configurable. Invalid input returns JSON 4xx errors; unknown widgets return 404; bursts return 429.

## Configuration

Copy `.env.example` to `.env`. Mock geo mode is deterministic and offline-safe for acceptance probes. Set `GEO_MODE=live` to use the two free provider APIs during manual development. `MOCK_PROVIDER_A_UP=false` demonstrates fallback to provider B; turn both mock providers off to demonstrate storage without geo. Set `FORCE_NOTIFY_FAIL=true` to demonstrate notification retries; submission success remains independent.

The rate limiter uses an in-process memory backend, suitable for the single-instance capstone demo. A multi-instance deployment should use shared storage such as Redis. Set a unique `JWT_SECRET` and restrict `CORS_ALLOW_ORIGINS` for any public deployment. The demo's default wildcard CORS is deliberate because customer websites may be on arbitrary origins; auth routes do not enable credentialed cookies.

## Migrations and checks

Schema changes live in Alembic migrations. Apply them with `alembic upgrade head`; generate a future migration with `alembic revision --autogenerate -m "describe change"` and inspect the generated diff before applying it. Run the acceptance tests with:

```powershell
pytest -v
```

`capstone.yaml` provides the evaluator run, seed, test, base URL, and probe endpoints. `EVIDENCE.md` records reproducible output for each acceptance item.

## Limitations

- The notification worker is a durable database outbox processed as a FastAPI background task. It retries three times with backoff and leaves failed jobs inspectable; a larger installation should run `retry_due_jobs()` from a dedicated scheduled worker and route exhausted failures to an alerting system.
- Geo lookups use public free APIs and should be cached and privacy-reviewed before higher volume use. Mock mode is for repeatable demonstrations.
- This is a local capstone app. Public hosting, TLS/domain, real email delivery, advanced visual design, and shared rate-limit storage are outside the scope.
- The repository must be published as its own public GitHub repository by the author before submission; this local workspace is not connected to a Git remote.

## Project notes

- [DESIGN.md](DESIGN.md) — data model, boundaries, and architecture decisions
- [EVIDENCE.md](EVIDENCE.md) — requirement-by-requirement proof
- [BUILDLOG.md](BUILDLOG.md) — AI assistance and author reflection
- [LICENSE](LICENSE) — MIT License
