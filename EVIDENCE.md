# Acceptance evidence

Captured from the local demo build with `AI_PROVIDER=demo`, threshold `0.20`, SQLite, 50 seeded images, and ten labeled posts. The sample is deterministic and offline; demo-catalog results are fixture metadata, not model vision output.

## Vision schema, low confidence, and batch processing

```text
POST /jobs/vision → 202
GET /jobs/f4feb509-56e5-41ad-bb5c-cbec70fe2200
{"status":"completed","total":50,"processed":50,"succeeded":50,"failed":0,"attempts":50}
GET /images: 50 total, 49 completed, 1 needs_review, 0 failed
Sample completed tags: attributes, caption, category, confidence, subject
The single needs_review image is the curated gray-wolf item at confidence 0.38 (< MIN_CONFIDENCE 0.55).
```

## Matching, synonym, mismatch guard, and no-match

```text
GET /posts/post-animals-01-02/images
status=matched, top image=img-animals-01-02, similarity=0.465, confidence=0.96

POST /posts (title="Vulpes vulpes habitat", expected_subject="red fox") + GET /posts/{new_id}/images
status=matched, subject=red fox

GET /posts/post-animals-01-02/images?force_image_id=img-animals-02-02
status=no_confident_match
reason="Subject mismatch: expected red fox, detected gray wolf"

POST /posts {"title":"Orbital telescope project","body":"The team built an orbital telescope to observe distant galaxies.","expected_category":"objects","expected_subject":"space telescope"} → 201
GET /posts/{new_id}/images
status=no_confident_match
reason="Category mismatch: expected objects, detected vehicles"
```

## Evaluation

```text
python eval.py
{"cases":10,"correct":10,"top1_precision":1.0,...}
TOP1_PRECISION=1.0000 (10/10)
```

## Per-call cost attribution

```text
GET /costs: 110 calls, total_cost_usd=0.0, budget_usd=0.50
image_embedding: 50 calls / $0.0
post_embedding: 10 calls / $0.0
vision: 50 calls / $0.0
The 50 vision calls use provider=demo-catalog; 100 embeddings use provider=local-hash.
Each log row includes provider, operation, model, image_id or post_id, job_id, status, duration, cost, and error.
```

## Shared backend checks

- Layered architecture: routes in `app/main.py`, schemas in `app/schemas.py`, use cases/providers in `app/services/`, tables/indexes in `migrations/0001_initial.sql` and tenant scope in `migrations/0002_tenant_scope.sql`.
- Boundary validation: malformed `POST /posts` body returned `422 Unprocessable Content`.
- Human review: approving the fox suggestion returned `200` with `review_status=approve`.
- Tenant scope: `GET /posts` and `GET /images` with `X-Tenant-ID: review-b` returned empty collections, and requesting the seeded demo post under that tenant returned `404`.
- Local UI/static checks: `/`, `/docs`, and `/media/img-animals-01-02.png` returned `200`.
- Batch retry safety: after successful processing, starting another vision job returned `total=0`; only pending/failed/interrupted records are processed.
- Secret handling: `.env` is ignored, `.env.example` contains a blank `GEMINI_API_KEY`, and Gemini reads it server-side. No API key was committed or sent to the browser.
- Image upload acceptance: a 64×48 PNG multipart upload returned `201`, appeared in `GET /images`, and its normalized JPEG returned `200 image/jpeg` from `/media/...`. The manual acceptance record was removed after verification.
- Historical provider check: the previously configured NVIDIA credential returned HTTP `401 Unauthorized` (`Authentication failed`). After the local configuration was updated, `AI_PROVIDER=nvidia`, model `z-ai/glm-5.3-flash`, and a non-empty local key were confirmed without displaying the key.
- Live NVIDIA image smoke check: the project's `AIProvider.classify()` sent `data/images/img-animals-01-01.png` (the generated illustration visibly labeled “RED FOX”) to `z-ai/glm-5.3-flash`. The first response contained valid tags inside a Markdown JSON fence and was rejected by the strict parser. After adding fence handling while retaining `ImageTags` schema validation, a repeat live request succeeded in 72.6 seconds: subject `red fox`, category `animal illustration`, confidence `0.95`, with 410 input and 307 output tokens. This is one smoke check on a labeled illustration, not a representative photo benchmark. This direct call was not persisted to the `/costs` ledger; no billing amount is claimed by this record.
- Mismatch reasons: the forced wolf is rejected by subject; the unsupported telescope story returns `no_confident_match` and ranked rejection reasons.

The 100% precision above is on ten deliberately small labeled demo cases with curated fixture tags. It is evidence that the evaluator path runs and the guard behaves on these probes, not a claim of general model accuracy. Upload acceptance verifies the local media path. Live NVIDIA API and tag-schema compatibility succeeded on one smoke image, but the model has not been evaluated on a representative licensed photo set.
