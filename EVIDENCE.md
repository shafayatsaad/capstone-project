# Acceptance evidence

Evidence below comes from the current local workspace. Automated checks were run on Python 3.13.11 with the bundled SQLite configuration. The two-origin browser proof used API origin `http://localhost:8000` and demo origin `http://localhost:5500`.

## Widget management and isolation

- [x] Authenticated CRUD endpoints; unauthenticated requests rejected.
- [x] Tenant A cannot read, update, or delete tenant B's widget.
- Proof: `tests/test_platform.py::test_auth_and_widget_crud_are_tenant_scoped` — **PASSED**.

## Widget delivery

- [x] Owner receives a versioned embed snippet; edits increment the widget version.
- [x] Public config uses `Cache-Control: public, max-age=60`.
- [x] Public JavaScript bundle uses a one-year immutable cache header.
- Proof: `tests/test_platform.py::test_widget_update_versions_embed_config_and_bundle_cache` — **PASSED**.
- Browser proof: opened the seeded widget from the page at `http://localhost:5500/`; the browser loaded `/widget.js` and `/widgets/{id}/config` from `localhost:8000`, submitted the form, and displayed `Thanks! Your response has been received.` Server log: `OPTIONS /submissions 200`, then `POST /submissions 201`.

## Public submission API

- [x] Cross-origin request and preflight work.
- [x] Malformed, missing, oversized, too-many-field, and widget-contract-invalid payloads return clean 4xx JSON.
- [x] Valid submissions persist against the requested widget and appear in the authenticated owner's dashboard.
- Proof: `tests/test_cors.py::test_cross_origin_submission_is_accepted`, `tests/test_cors.py::test_preflight_options_request_is_handled`, `tests/test_validation.py::*`, and `tests/test_platform.py::test_submission_checks_the_widget_field_contract` — **PASSED**.
- Browser proof above exercised a real cross-origin browser preflight and submission.

## Abuse protection

- [x] Per-IP burst limit returns 429 while `/health` remains available.
- [x] Honeypot submissions receive a success-shaped response but are not stored.
- Proof: `tests/test_rate_limiting.py::test_burst_of_requests_returns_429_then_recovers` and `tests/test_spam.py::test_honeypot_fill_is_silently_dropped` — **PASSED**.

## Enrichment and safe side effects

- [x] Provider A failure falls back to provider B.
- [x] Both providers failing leaves geo empty and still stores the lead.
- [x] Notification failure does not fail the lead; outbox retries three times and records the exhausted job.
- Proof: `tests/test_enrichment.py::*`, `tests/test_notify.py::test_failing_notify_side_effect_does_not_break_submission`, and `tests/test_notification_worker.py::test_failed_notification_retries_and_keeps_submission_successful` — **PASSED**.

## Shared capstone checks

- [x] Background job with retries and failure alert log: notification outbox tests above.
- [x] Migration and indexed schema: fresh `alembic upgrade head` succeeded; `alembic check` reported `No new upgrade operations detected.`
- [x] Idempotent public submission retries return the original record: `tests/test_platform.py::test_idempotency_key_returns_the_original_submission` — **PASSED**.
- [x] Secrets use environment configuration; `.env` is ignored and `.env.example` contains placeholders. No runtime AI API or paid service is used.
- [x] README includes architecture, setup, API summary, limitations, and the manifest/evidence/build log.

## Captured test run

```text
python -m pytest -q
.....................                                                    [100%]
21 passed in 2.41s
```

Fresh local setup output:

```text
python -m alembic upgrade head
Running upgrade  -> 0001_initial, Initial schema for owners, widgets, submissions, and notification outbox.
python seed.py
Seed complete.
demo widget_id = 00000000-0000-0000-0000-0000000000aa
```

`docker compose config` parsed the Compose file successfully. The Docker CLI is installed, but the Docker Desktop Linux engine was stopped on this host, so the containerized Postgres launch could not be exercised here.

## Submission pack status

- [x] `README.md`
- [x] `capstone.yaml`
- [x] `EVIDENCE.md`
- [x] `BUILDLOG.md`
- [x] `.env.example`
- [x] MIT license
- [ ] Create/publish the dedicated public GitHub repository and preserve the build history. This local folder has no `.git` directory or GitHub remote, so publication has not been performed.
- [ ] Author: complete the reflection prompts in `BUILDLOG.md` in your own words before a live evaluation.
