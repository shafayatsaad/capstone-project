# EVIDENCE.md

One pasted proof per requirement from Section 6 of the brief. Replace each
`<PASTE OUTPUT HERE>` with the real output from your own machine — a screenshot
description, curl transcript, or pytest output. Claims without evidence score
as not done, so don't skip this.

## Widget management — Phase 3, not built yet
- [ ] Authenticated CRUD endpoints; unauthenticated requests rejected
- [ ] Multi-tenant isolation proven

## Widget delivery — Phase 3, not built yet
- [ ] Embed snippet generated per widget
- [ ] Public config endpoint with correct cache headers
- [ ] Versioned bundle

## Public submission API — Phase 2 ✅

- [x] **Cross-origin submissions work: CORS headers correct, preflight handled.**
  Run: `pytest tests/test_cors.py -v`
  ```
  <PASTE OUTPUT HERE>
  ```
  Or manually, from a second-origin static server:
  ```
  curl -i -X OPTIONS http://localhost:8000/submissions \
    -H "Origin: http://localhost:5500" \
    -H "Access-Control-Request-Method: POST"
  ```
  ```
  <PASTE OUTPUT HERE>
  ```

- [x] **All incoming input validated; malformed/oversized payloads rejected with 4xx + JSON errors.**
  Run: `pytest tests/test_validation.py -v`
  ```
  <PASTE OUTPUT HERE>
  ```

- [x] **Valid submissions stored safely, linked to the right widget and tenant.**
  Run: `python seed.py` then the curl command it prints, then check the row:
  ```
  <PASTE OUTPUT HERE>
  ```

## Abuse protection — Phase 2 ✅

- [x] **Rate limiting per IP returns 429 under a burst — API keeps serving legitimate traffic.**
  Run: `pytest tests/test_rate_limiting.py -v`
  ```
  <PASTE OUTPUT HERE>
  ```

- [x] **At least one spam-prevention technique demonstrably blocks a spam submission.**
  Run: `pytest tests/test_spam.py -v`
  ```
  <PASTE OUTPUT HERE>
  ```

## Enrichment & safe side effects — Phase 2 ✅

- [x] **IP→geo enrichment uses a provider fallback chain: A down → B answers.**
  Run: `pytest tests/test_enrichment.py -v`
  ```
  <PASTE OUTPUT HERE>
  ```

- [x] **All providers down → submission still succeeds, without geo.**
  Same test file as above (`test_stores_without_geo_when_both_providers_down`).

- [x] **A failing confirmation email/webhook does not prevent the submission from being stored.**
  Run: `pytest tests/test_notify.py -v`
  ```
  <PASTE OUTPUT HERE>
  ```

## Documentation — in progress
- [ ] README with architecture diagram, setup instructions, API docs (Phase 3 finishes this)
