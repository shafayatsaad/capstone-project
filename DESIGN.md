# Design: AI Image Understanding and Content Matching

## Problem and scope

Given a small image library and editorial posts, describe and tag each image, rank useful images for each post, and refuse unsafe pairings with a human-readable reason. The important success case is that a fox article gets the fox and explicitly rejects a wolf, even though both are animals in a forest.

The first release targets a reproducible 50-record corpus, one FastAPI process, and SQLite. It supports three providers: a deterministic catalog provider for a no-key demo, local Ollama, and Gemini. The catalog provider makes API behavior and evaluation reproducible; it is not presented as a vision model. Use Ollama or Gemini to actually interpret image bytes.

## Data model

- `images`: source, expected demo label, validated tags, confidence, classification state, retry count, and caption embedding.
- `posts`: title/body, labeled expected category and subject for evaluation, and content embedding.
- `suggestions`: ranked candidates, similarity, guard decision/reason, and human review state.
- `jobs`: asynchronous batch progress and failures.
- `ai_calls`: provider, operation/model, image/post/job attribution, status, duration, and cost per operation.
- `evaluation_runs`: tenant-scoped precision result and the expected/predicted pairs from each run.
- `tenant_id`: a workspace scope on every mutable record, injected by the `X-Tenant-ID` request header and included in lookup indexes.

SQLite migrations create indexes for image processing state, category/subject lookup, post labels, review state, job state, cost-log time/job queries, and tenant-scoped lookups.

## API surface

`GET /health`, `GET /images`, `POST /jobs/vision`, `GET /jobs/{id}`, `GET/POST /posts`, `GET /posts/{id}/images`, `POST /suggestions/{id}/review`, `GET /costs`, and `POST /eval/run`. Data endpoints scope by `X-Tenant-ID` (default `demo`).

`GET /posts/{id}/images?force_image_id=...` exercises the guard against a specified candidate. It is useful for proving the wolf/fox rejection and does not bypass the guard.

## Layers and request flow

```text
HTTP (FastAPI routers + Pydantic boundary schemas)
       ↓
Use cases (batch orchestration, retrieval, mismatch guard, review, evaluation)
       ↓
Provider interface (demo catalog | Ollama | Gemini)
       ↓
SQLite repository (migrations, vectors/tags, jobs, reviews, attributed cost log)
```

Vision tagging runs in a FastAPI background task, with retry/backoff and progress persisted after each image. Matching embeds descriptions and post text in the same space, ranks by cosine similarity, then checks tag/subject compatibility, model confidence, and a tuned similarity threshold. Low confidence and unclassified images are never offered as accepted matches.

## Guard decisions

1. Reject if an image is not classified or has low confidence.
2. Reject category mismatches.
3. Reject different labeled subjects within a category (for example fox vs wolf), with an explicit explanation.
4. Reject if semantic similarity is below `MIN_SIMILARITY`.
5. Otherwise accept and return the ranked recommendation with its score and reason.

For a production corpus, replace the demo labels with model-produced tags and calibrate the threshold on the included labeled evaluation set. The rule-based expected subject is also the ground-truth label for eval, not a production inference feature.

## Explicit non-goals

No public hosting or tenant authentication, image-upload UI, vector database, or automatic image licensing crawler. Workspace IDs isolate database queries but are not credentials. The corpus and model/provider remain small and inspectable.
