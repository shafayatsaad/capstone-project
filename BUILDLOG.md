# BUILDLOG — AI assistance and reflection

The capstone brief permits AI assistance and asks the author to describe where it helped, where it was wrong, and what the author changed. Keep this log truthful and edit the author-reflection section in your own words before presenting the project.

## Phase 1 — design

- The original project notes say Claude helped draft the initial design. The data model and intended tenant boundary were reviewed in the project notes.
- Codex reviewed the attached brief and the workspace, then updated this design to reflect the implemented API and persistence model.

## Phase 2 — hardened submission path

- Existing app code used AI-assisted scaffolding for FastAPI, boundary validation, CORS, rate limiting, honeypot spam control, geo fallback, notification behavior, and tests.
- During this review, verification found that a Pydantic validation detail contained a raw `ValueError` and could itself cause a 500. The response now omits non-serializable exception context.
- The original spam code persisted honeypot hits even though the evaluator probe calls for a silent drop or rejection. It now returns the ordinary success shape without persisting a lead.
- The existing Windows test teardown left SQLite open. The fixture now disposes the SQLAlchemy engine before removing the test database.

## Phase 3 — delivery, dashboard, and hardening

- Codex implemented owner registration/login, signed bearer tokens, widget CRUD with tenant filtering, public config and bundle routes, the JavaScript embed, owner dashboard endpoints, a versioned snippet, idempotency, Alembic migrations, and the notification outbox.
- The notification outbox and submission are stored in the same transaction. The background task retries three times and records terminal failures; a small system can later run the due-job function on a schedule.
- Automated checks run during this review: `pytest -q` reported 21 passing tests; a fresh `alembic upgrade head`, `alembic check`, and `python seed.py` completed against local SQLite. The seeded widget also rendered and submitted successfully from the separate-origin browser demo.

## Author reflection — complete before interview/demo

Write these in your own words after you have run the project and can explain the tradeoffs:

1. Why does every owner-facing lookup filter through `Widget.owner_id`, and what test proves a second owner cannot read another owner's widget?
2. Why does a submission and its notification job share a transaction? What happens after the notification fails all retries?
3. Why does the public config use a short cache while the widget bundle is immutable and versioned?
4. What would you change first to support multiple API instances safely?

Suggested code to study and explain: `app/security.py` token signing and password hashing; `app/services/submission_service.py` validation and idempotency ordering; `app/services/notification_worker.py` retry state transitions. Do not claim personal work or understanding you have not verified.
