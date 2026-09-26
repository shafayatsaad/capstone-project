# Fieldnote — AI Image Understanding & Content Matching Engine

Fieldnote reads an image library, tags images, ranks them for editorial stories, and explains when it refuses a pairing. A red-fox article should find the fox; a wolf, a dog, or a poor-confidence image should never sneak through just because it looks plausible.

This is a compact FlyRank backend capstone built with FastAPI and SQLite. The default catalog provider is deterministic and offline, so an evaluator can reproduce the full acceptance path without API keys, local model downloads, or a credit card. It deliberately uses curated metadata fixtures and labels them as such; it does **not** claim the fixture provider performed computer vision. Switch to Ollama to run real image and embedding models locally.

## See it run

The browser dashboard at `http://localhost:8000` shows the 50-image library, batch progress, article matches, rejected candidates with reasons, human review actions, tracked calls, and the labeled-set score. API docs are at `/docs`.

```text
Article: “Red fox habitat”
Top pick: red fox illustration          similarity 0.47 · confidence 0.96
Forced candidate: gray wolf illustration
REJECTED: Subject mismatch: expected red fox, detected gray wolf
```

## Architecture

```text
Dashboard / API
      ↓ Pydantic validation
FastAPI routes ──→ matching + mismatch guard + review + evaluation
      │                         │
      ├─ background batch ──→ provider interface (offline catalog | Ollama)
      │                         ├─ validated vision tags
      │                         └─ image/post embeddings
      ↓
SQLite repository (SQL migration, indexes, jobs, suggestions, reviews, per-call costs)
```

Images and posts are embedded in the same vector space, ranked by cosine similarity, then checked in a separate guard. The guard rejects unclassified/low-confidence images, category mismatches, wrong subjects (including fox-vs-wolf), and scores below `MIN_SIMILARITY`. Refusals include a human-readable reason. A forced-candidate query still runs every guard check.

The schema is initialized from ordered SQLite migrations. Every image, post, suggestion, batch job, and AI-call record has a `tenant_id`; data API queries are scoped by the `X-Tenant-ID` header (default `demo`) and tenant-aware indexes. HTTP schemas reject invalid payloads with clean 4xx responses. SQLite foreign keys and transactions protect relationships. The workspace identifier gives query isolation; it is not authentication, so this local showcase must not be exposed as a public multi-user service.

## Run locally

Requires Python 3.11+.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python seed.py
python -m uvicorn app.main:app --reload
```

Open [http://localhost:8000](http://localhost:8000), select **Classify image library**, then try the red-fox article and press **Try guard** on the wolf alternative. The seeded offline catalog completes in a few seconds. To reproduce the evaluation from a second terminal, run `python eval.py` after classification. Data and 50 small original demo illustrations are stored under `data/`.

### Docker

```powershell
Copy-Item .env.example .env
docker compose up --build -d
docker compose exec app python seed.py
```

Open `http://localhost:8000`; the first process starts an empty database and the seed command writes demo data to the persisted `data` volume.

## Real local AI with Ollama (optional)

The demo works without Ollama. For actual image understanding, install Ollama and pull a vision model plus an embedding model (for example `llava` and `nomic-embed-text`). Set `AI_PROVIDER=ollama` in `.env`, confirm both model names, and run the batch. Ollama runs locally and this configuration makes no cloud API calls. The adapter uses Ollama's chat endpoint for image input and structured JSON, and `/api/embed` for text vectors; use the same embedding model on image captions and article text ([chat/API docs](https://github.com/ollama/ollama/blob/main/docs/api.md), [embedding docs](https://github.com/ollama/ollama/blob/main/docs/capabilities/embeddings.mdx)). Images are generated, labeled illustrations; use a varied set of licensed photographs for a production quality comparison. Both outputs are schema-validated before persistence. Invalid model responses fail and retry; low confidence is held for review.

Embeddings use Ollama's `/api/embed` when configured. The offline provider uses a transparent deterministic semantic hash with explicit synonym normalization (including “Vulpes vulpes” and “red fox”). It is for repeatable capstone probes and is not a replacement for a trained embedding model.

## API quick reference

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Service and selected provider |
| `GET` | `/images` | Image state, tags, and confidence |
| `POST` | `/jobs/vision` | Start a background batch; returns `202` |
| `GET` | `/jobs/{id}` | Progress, failures, and completion state |
| `GET/POST` | `/posts` | List demo stories or create a validated post |
| `GET` | `/posts/{id}/images` | Ranked matches, refusal reasons, and review IDs |
| `GET` | `/posts/{id}/images?force_image_id=img-animals-02-02` | Force the wolf candidate for a fox post and inspect the guard |
| `POST` | `/suggestions/{id}/review` | Approve or reject a suggestion with an optional note |
| `GET` | `/costs` | Per-call log, totals, budget, and grouping by operation |
| `POST` | `/eval/run` | Evaluate the labeled set and report top-1 precision |
| `GET` | `/eval/latest` | Latest persisted evaluation score for the workspace |

The batch is safe to retry: successful rows are not processed again, failed and interrupted rows are retryable, and concurrent active jobs return `409`. Every vision and embedding operation is attributed to its image/post/job, including errors. The default local and fixture providers cost `$0`; the configured budget is visible in `/costs`. No metered cloud provider is enabled in this build.

All data endpoints accept `X-Tenant-ID`; omit it for the seeded `demo` workspace. To compare isolation, create a post with `X-Tenant-ID: review-a`, then request it with `X-Tenant-ID: review-b` and receive `404`. This identifier scopes data but does not prove user identity.

## Evaluation

The labeled set contains ten posts from five categories. `python eval.py` and `POST /eval/run` classify any pending corpus first, then report top-1 precision as `TOP1_PRECISION=...` and show each expected and predicted image ID. The captured offline acceptance run measured `100%` top-1 precision on these ten fixtures. This is a small, curated demo set rather than a general model quality claim; see `EVIDENCE.md` for the full result.

## Configuration

See `.env.example`: provider, database path, model names, confidence and similarity thresholds, retry count/backoff, and cost budget. Secrets are read from environment only; no key is needed by the included providers. Never commit `.env` or model credentials. For a hosted instance, restrict CORS, use HTTPS, add authentication, and store secrets with the host's secret manager.

## Limitations

- The included original geometric illustrations and catalog tags prove the decision flow, not the accuracy of a vision model on photographs. The demo provider is explicitly labeled in every cost entry. Replace the artwork with a small licensed corpus and run Ollama to evaluate actual visual recognition.
- The offline hash embedding is small and synonym-aware for the capstone vocabulary, but it is not a general semantic model. Ollama embeddings improve paraphrase coverage.
- SQLite, in-process FastAPI background tasks, and unauthenticated workspace IDs suit a single-process review; use a durable queue, shared vector store, real identity-to-tenant authorization, and stronger persistence for production.
- Model “confidence” is a self-reported signal, not a calibrated probability. The threshold should be tuned against more labeled examples before real editorial use.
- Static demo image paths are local paths; arbitrary remote user image uploads are outside scope.

## Project notes

- [DESIGN.md](DESIGN.md) — data model, API, decision rules, and explicit non-goal.
- [EVIDENCE.md](EVIDENCE.md) — acceptance probe transcripts captured from the current build.
- [BUILDLOG.md](BUILDLOG.md) — AI assistance and ownership reflection.
- [capstone.yaml](capstone.yaml) — evaluator run, seed, evaluation command, and probe endpoints.
- [LICENSE](LICENSE) — MIT license; generated demo artwork is original to this project.

## Public repository submission

The capstone brief requires a **dedicated public GitHub repository** named `flyrank-capstone-image-relevance`. This workspace's Git history contains a different earlier capstone, so do not present this repository history as satisfying that rule. Publish the finished source in a new dedicated public repository, add its remote, and submit that repository URL through the portal. Never upload a ZIP.
