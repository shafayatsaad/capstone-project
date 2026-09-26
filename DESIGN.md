# Design — Embeddable Widget & Lead-Capture Platform

## Problem and scope

Customers need to collect signups and contact requests from websites they do not control without operating a backend. The product gives an owner a tenant-scoped widget API and one script tag. Visitors load public config and submit through a hardened cross-origin endpoint; the owner reads stored leads and basic analytics through an authenticated dashboard API.

The system focuses on the difficult boundary: public input, unpredictable origins and traffic, and external services that may fail. It does not include a visual widget builder, public hosting, or production email delivery.

## Data model

- **Owner**: UUID-like string ID, unique indexed email, PBKDF2 password hash, creation time.
- **Widget**: ID, indexed `owner_id`, supported type, validated title/description/field definitions, display options, version, timestamps. Every admin query filters by both widget ID and the authenticated owner's ID.
- **Submission**: ID, widget ID, bounded JSON fields, IP, optional geo, spam flag, creation time, optional idempotency key. `(widget_id, idempotency_key)` is unique, so safe client retries return the original submission.
- **NotificationJob**: durable outbox item with unique submission ID, pending/sent/failed status, attempt count, next retry time, and last error. It is committed with the submission so the notification is not lost between persistence and response.

Alembic owns the schema (`migrations/`). SQLite is the quick local default; Docker Compose uses PostgreSQL.

## Request paths

```text
Owner -> register/login -> signed bearer JWT
  -> Widget CRUD (every read/write owner-scoped) -> embed snippet with widget version

Customer page -> GET /widget.js (immutable cache)
  -> GET /widgets/{id}/config (60-second cache)
  -> render a small safe DOM form -> POST /submissions

Submission -> byte/schema/field-contract validation -> per-IP rate limit
  -> honeypot silent drop -> geo A -> geo B -> no geo if both fail
  -> transaction: submission + notification outbox -> success response
  -> background notification retries; exhaustion is logged as an alert

Owner -> dashboard submissions/stats (joins through Widget and filters owner_id)
```

## API surface

- `POST /auth/register`, `POST /auth/login`
- `POST/GET /widgets`, `GET/PUT/DELETE /widgets/{id}`, `GET /widgets/{id}/embed`
- Public `GET /widget.js`, `GET /widgets/{id}/config`
- Public `POST /submissions`
- Owner-scoped `GET /dashboard/submissions`, `GET /dashboard/stats`
- `GET /health`

## Design decisions

- The browser embed uses DOM text nodes rather than injecting widget-provided HTML.
- Submitted keys must match the widget's field contract; required values, request size, field count, and value lengths are checked before persistence.
- Spam is silently dropped with a success-shaped response to avoid teaching bots how detection works and to satisfy the acceptance probe. It is not stored or counted as a lead.
- Geo enrichment is best effort. Mock providers make fallback tests deterministic; live free providers are optional.
- The notification outbox is persisted with the lead. FastAPI BackgroundTasks perform three attempts with backoff, and failed jobs remain queryable for a scheduled recovery worker.
- JWTs use HMAC-SHA256 and passwords use PBKDF2-HMAC-SHA256 from the Python standard library. A deployment must set a unique `JWT_SECRET` and use TLS.
- Rate limiting uses a process-local backend, adequate for the capstone's single instance. A multi-instance deployment needs shared storage.

## Explicit non-goals

Visual drag-and-drop editing, a full owner web UI, real SMTP, hosted production infrastructure, shared distributed rate limits, and advanced bot challenges. The focus is API behavior, resilience, and evidence that the acceptance probes pass.
