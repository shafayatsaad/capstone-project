# BUILDLOG.md

Honest log of where AI (Claude) helped, where it was wrong or needed correction,
and what I changed. This is graded on honesty, not on minimizing AI use.

## Phase 1 — Design
- Used Claude to draft the initial DESIGN.md structure (data model, API surface,
  layer sketch) based on the capstone brief.
- I reviewed the tenant-isolation approach and confirmed it matches how I want
  auth to work in Phase 3 (owner_id on Widget, joined through for Submission).

## Phase 2 — Hardened submission path
- Used Claude to scaffold the FastAPI app: config, models, the submission
  pipeline (validation → spam check → enrichment → store → notify), the geo
  fallback chain with a mock mode, slowapi rate limiting, and a pytest suite
  covering each requirement.
- What I changed / verified myself:
  - <FILL IN: e.g. "adjusted MAX_PAYLOAD_BYTES after testing with my actual
    widget field sizes" or "renamed the honeypot field to avoid an obvious name">
  - <FILL IN: any bug you found while running `pytest` locally that wasn't
    caught before, and how you fixed it>
- I can explain: the spam-handling design choice (spam submissions get a
  normal-looking 201 instead of a rejection, to avoid tipping off bots — see
  the docstring in `app/services/spam_service.py`), and why enrichment/notify
  failures are caught in two places (inside their own service functions *and*
  again in `submission_service.py`) rather than relying on a single try/except.
- <FILL IN: pick 2-3 specific lines/functions from the code and note, in your
  own words, why they're written the way they are — this is what an evaluator
  will ask you to do live, so writing it down now is good practice for that>
