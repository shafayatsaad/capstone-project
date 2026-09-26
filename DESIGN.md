# Design Doc — Embeddable Widget & Lead-Capture Platform

**Author:** Md. Shafayat Sadat Saad · **Stack:** Python + FastAPI · **Status:** Phase 1 (design)

## 1. Problem

Customers need a way to collect leads (signups, contact requests, CTA clicks) from their own websites
without writing backend code. They should be able to define a widget once, get a single `<script>` tag,
and have submissions land — validated, spam-filtered, geo-enriched — in a dashboard they can see.
The hard part isn't the CRUD; it's that the public submission endpoint receives traffic from browsers
we don't control, on origins we don't control, at a rate we don't control. The system has to stay up and
stay honest under that.

## 2. Data model

**Owner** (tenant / customer account)
| column | type | notes |
|---|---|---|
| id | UUID, PK | |
| email | text, unique | |
| password_hash | text | bcrypt |
| created_at | timestamptz | |

**Widget** (belongs to exactly one Owner — this *is* the tenant boundary)
| column | type | notes |
|---|---|---|
| id | UUID, PK | used in the embed URL (`?id=`) |
| owner_id | UUID, FK → Owner, **indexed** | every query on Widget is scoped by this |
| type | enum(`signup_form`, `cta`, `popover`) | |
| title, description | text | |
| fields | JSONB | field definitions (name, label, type, required) |
| button_text | text | |
| display_options | JSONB | color/position/etc., kept minimal |
| version | integer, default 1 | bumped on config-affecting edits → cache-busts the bundle URL |
| created_at, updated_at | timestamptz | |

**Submission** (belongs to exactly one Widget, which fixes its tenant transitively)
| column | type | notes |
|---|---|---|
| id | UUID, PK | |
| widget_id | UUID, FK → Widget, **indexed** | |
| data | JSONB | the submitted form fields, post-validation |
| ip_address | inet | raw submitter IP, kept for enrichment + rate limiting |
| geo_country, geo_city | text, nullable | filled by enrichment; null if all providers failed |
| is_spam | boolean, default false | set by the honeypot/heuristic check |
| created_at | timestamptz, **indexed** | dashboard time-series queries filter/sort on this |

**Tenant isolation rule:** every Widget query filters `WHERE owner_id = :current_owner_id`; every
Submission query joins through Widget and filters the same way. This is enforced once, in a repository
layer, so no route can accidentally skip it.

## 3. The embed flow

```
1. Owner creates a widget          → POST /widgets              (authenticated)
2. Owner is given a snippet        → GET  /widgets/:id/embed     (authenticated)
     <script src="https://api.example.com/widget.js?id=<uuid>&v=<version>"></script>
3. Customer pastes that tag into their site (a different origin)
4. Visitor's browser loads /widget.js         → public, versioned, cached long
5. widget.js calls GET /widgets/:id/config    → public, cached short, CORS-enabled
6. widget.js renders the form from that config
7. Visitor submits  → POST /submissions        → public, CORS + preflight, protected
8. Response shown inline in the widget; owner sees it moments later on the dashboard
```

## 4. API surface

**A — Widget management (authenticated, tenant-scoped)**
- `POST /auth/register`, `POST /auth/login` → JWT
- `POST /widgets` · `GET /widgets` · `GET /widgets/:id` · `PUT /widgets/:id` · `DELETE /widgets/:id`
- `GET /widgets/:id/embed` — returns the ready-to-paste `<script>` string
- `GET /dashboard/submissions?widget_id=` · `GET /dashboard/stats?widget_id=` — counts over time, geo breakdown

**B — Public widget delivery (public, cached)**
- `GET /widget.js` — versioned JS bundle, `Cache-Control: public, max-age=31536000, immutable`
- `GET /widgets/:id/config` — JSON config, `Cache-Control: public, max-age=60`, CORS allow-all-origins

**C — Public submission (public, CORS, protected)**
- `POST /submissions` — body `{ widget_id, fields: {...}, hp_field: "" }`
  - 201 on success, 4xx on bad/oversized payload, 429 on rate limit
- `OPTIONS /submissions` — preflight, handled by CORS middleware, not a hand-written route

## 5. Layer sketch

```
routers/            → HTTP only: parse request, call a service, shape response
  admin_widgets.py
  public_delivery.py
  public_submissions.py
  dashboard.py

services/            → business rules, no HTTP, no SQL
  widget_service.py       (CRUD + snippet generation)
  submission_service.py   (validate → spam check → rate limit → enrich → store → side effect)
  enrichment_service.py   (provider A → provider B → give up cleanly)
  notify_service.py       (email/webhook; failure is swallowed + logged, never raised upward)

repositories/         → SQL only, tenant filtering lives here
  widget_repo.py
  submission_repo.py

middleware/
  cors.py · rate_limit.py

models/               → SQLAlchemy models + Pydantic schemas
db/                   → engine, session, migrations (Alembic)
```

Request path for a submission: `router → validate schema → rate_limit middleware → spam check →
enrichment_service (fallback chain) → submission_repo.create() → notify_service (best-effort,
backgrounded) → 201 response`. Nothing after "store" can turn a success into a failure.

## 6. Non-goal (explicit)

**Out of scope for this capstone:** a visual drag-and-drop widget builder. Widget configuration is done
via the JSON API only, and the rendered widget itself is a minimal, unstyled HTML form — the grade and
the engineering value here are in the backend (auth, CORS, abuse protection, enrichment, degradation),
not in a themable front-end design system. A prettier widget is a stretch goal, not a requirement.
