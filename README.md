# Fieldnote — AI Image Understanding & Content Matching Engine

Fieldnote reads an image library, tags images, ranks them for editorial stories, and explains when it refuses a pairing. A red-fox article should find the fox; a wolf, a dog, or a poor-confidence image should never sneak through just because it looks plausible.

This is a compact FlyRank backend capstone built with FastAPI and SQLite. The default catalog provider is deterministic and offline, so an evaluator can reproduce the full acceptance path without API keys, local model downloads, or a credit card. It deliberately uses curated metadata fixtures and labels them as such; it does **not** claim the fixture provider performed computer vision. Switch to Gemini, NVIDIA, or Ollama to run real image and embedding models.

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
FastAPI routes ──→ upload + matching + mismatch guard + review + evaluation
      │                         │
      ├─ background batch ──→ provider interface (offline catalog | Gemini | NVIDIA | Ollama)
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
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
python seed.py
python -m uvicorn app.main:app --reload
```

Open [http://localhost:8000](http://localhost:8000), select **Classify image library**, then try the red-fox article and press **Try guard** on the wolf alternative. Upload JPG, PNG, or WebP images from the **Add an image** form; uploads are normalized and queued for the next batch. To reproduce the evaluation from a second terminal, run `python eval.py` after classification. Data and 50 small original demo illustrations are stored under `data/`.

### Docker

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
docker compose up --build -d
docker compose exec app python seed.py
```

Open `http://localhost:8000`; the first process starts an empty database and the seed command writes demo data to the persisted `data` volume.

## Real image analysis with Gemini API

Create an API key in [Google AI Studio](https://aistudio.google.com/app/apikey). Keep it private: edit the local `.env` file and set `AI_PROVIDER=gemini` and `GEMINI_API_KEY=your-key`; then restart the app. Never paste the key into the dashboard, source code, screenshots, or GitHub. `.env` is gitignored. The browser only sees the selected provider name, never the key. The adapter sends image bytes to Gemini's `generateContent` endpoint with a JSON response schema, validates the response with Pydantic, and embeds image descriptions and article text with `embedContent`. After a real-provider batch, existing article vectors are rebuilt with that provider so similarity comparisons use the same vector space. Google documents [structured JSON output](https://ai.google.dev/gemini-api/docs/structured-output), [image-capable generation](https://ai.google.dev/api/generate-content), and [embeddings](https://ai.google.dev/api/embeddings).

For a clean real-model run, reset the seeded demo workspace, restart with Gemini enabled, and then classify the catalog and uploads:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
# Edit .env locally: AI_PROVIDER=gemini and set GEMINI_API_KEY (do not commit .env)
python seed.py
python -m uvicorn app.main:app --reload
```

Alternatively, upload from the dashboard and press **Classify image library**. You can call the multipart API directly:

```powershell
curl.exe -X POST http://localhost:8000/images -F "file=@.\my-image.jpg" -F "title=Forest fox" -F "category=animals"
```

Gemini token counts and estimated costs are recorded in `/costs`. `.env.example` contains default estimate rates for Gemini 2.5 Flash and Gemini Embedding; Google may change rates, and free-tier versus paid-tier billing depends on the API key's project. Check the [official pricing page](https://ai.google.dev/gemini-api/docs/pricing) and update `GEMINI_*_USD_PER_MILLION` to match the account/model before relying on the budget meter. The demo budget is `$0.50`. A missing or invalid key creates a batch failure with an actionable error; it never falls back silently to demo labels.

## NVIDIA API provider

For NVIDIA NIM, set `AI_PROVIDER=nvidia` and `NVIDIA_API_KEY` in `.env` using a key created for the NVIDIA API Catalog, then restart the server. The adapter calls the OpenAI-compatible NVIDIA chat completions endpoint with a base64 image data URL and validates the returned tag JSON. The sample configuration uses `z-ai/glm-5.3-flash`, which accepts images; this exact model was smoke-tested through the project's classifier. The `z-ai/glm-5.3` and `nvidia/nemotron-3-ultra-550b-a55b` examples are text-only and cannot classify uploaded images. `nvidia/nemotron-parse-2.0` accepts images but specializes in document OCR/layout extraction, so it is a poor fit for editorial photos. Image and article embeddings stay in the local semantic-hash space so they remain comparable. The provider call log records token usage; check the NVIDIA account's current access and usage terms before processing a large batch. Keep the key private and out of submitted files/screenshots.

## Real local AI with Ollama (optional)

For local model processing, install Ollama and pull a vision model plus an embedding model (for example `llava` and `nomic-embed-text`). Set `AI_PROVIDER=ollama` in `.env`, confirm both model names, and run the batch. Ollama runs locally and makes no cloud API calls. The adapter uses Ollama's chat endpoint for image input and structured JSON, and `/api/embed` for text vectors ([chat/API docs](https://github.com/ollama/ollama/blob/main/docs/api.md), [embedding docs](https://github.com/ollama/ollama/blob/main/docs/capabilities/embeddings.mdx)). Both model outputs are schema-validated before persistence. Invalid model responses fail and retry; low confidence is held for review.

Embeddings use Ollama's `/api/embed` when configured. The offline provider uses a transparent deterministic semantic hash with explicit synonym normalization (including “Vulpes vulpes” and “red fox”). It is for repeatable capstone probes and is not a replacement for a trained embedding model.

## API quick reference

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Service and selected provider |
| `GET` | `/images` | Image state, tags, and confidence |
| `POST` | `/images` | Upload a JPG, PNG, or WebP image (multipart `file`, optional `title`, `category`, `subject_hint`) |
| `POST` | `/jobs/vision` | Start a background batch; returns `202` |
| `GET` | `/jobs/{id}` | Progress, failures, and completion state |
| `GET/POST` | `/posts` | List demo stories or create a validated post |
| `GET` | `/posts/{id}/images` | Ranked matches, refusal reasons, and review IDs |
| `GET` | `/posts/{id}/images?force_image_id=img-animals-02-02` | Force the wolf candidate for a fox post and inspect the guard |
| `POST` | `/suggestions/{id}/review` | Approve or reject a suggestion with an optional note |
| `GET` | `/costs` | Per-call log, totals, budget, and grouping by operation |
| `POST` | `/eval/run` | Evaluate the labeled set and report top-1 precision |
| `GET` | `/eval/latest` | Latest persisted evaluation score for the workspace |

The batch is safe to retry: successful rows are not processed again, failed and interrupted rows are retryable, and concurrent active jobs return `409`. Every vision and embedding operation is attributed to its image/post/job, including errors. The default fixture and local providers cost `$0`; Gemini token usage and estimated costs are visible in `/costs`.

All data endpoints accept `X-Tenant-ID`; omit it for the seeded `demo` workspace. To compare isolation, create a post with `X-Tenant-ID: review-a`, then request it with `X-Tenant-ID: review-b` and receive `404`. This identifier scopes data but does not prove user identity.

## Evaluation

The labeled set contains ten posts from five categories. `python eval.py` and `POST /eval/run` classify any pending corpus first, then report top-1 precision as `TOP1_PRECISION=...` and show each expected and predicted image ID. The captured offline acceptance run measured `100%` top-1 precision on these ten fixtures. This is a small, curated demo set rather than a general model quality claim; see `EVIDENCE.md` for the full result.

## Configuration

See `.env.example`: provider, database path, model names, confidence and similarity thresholds, retry count/backoff, upload limit, and cost estimates. Demo and Ollama need no cloud key; Gemini reads `GEMINI_API_KEY` and NVIDIA reads `NVIDIA_API_KEY` from the local environment. In NVIDIA mode, the configured image-capable chat model classifies images while embeddings stay in the deterministic local space. Never commit `.env` or model credentials. For a hosted instance, restrict CORS, use HTTPS, add authentication, and store secrets with the host's secret manager.

## Limitations

- The included original geometric illustrations and catalog tags prove the decision flow, not the accuracy of a vision model on photographs. The demo provider is explicitly labeled in every cost entry. Replace the artwork with a small licensed corpus and run NVIDIA, Gemini, or Ollama to evaluate actual visual recognition.
- The offline hash embedding is small and synonym-aware for the capstone vocabulary, but it is not a general semantic model. Gemini or Ollama embeddings improve paraphrase coverage.
- SQLite, in-process FastAPI background tasks, and unauthenticated workspace IDs suit a single-process review; use a durable queue, shared vector store, real identity-to-tenant authorization, and stronger persistence for production.
- Model “confidence” is a self-reported signal, not a calibrated probability. The threshold should be tuned against more labeled examples before real editorial use.
- Uploads accept JPG, PNG, and WebP up to 5 MB and 25 megapixels, normalize to JPEG, and are stored under a workspace-hashed folder. This local showcase has no account authentication; a workspace header scopes data but is not an authorization boundary.
- `AI_PROVIDER=demo` is repeatable but does not inspect uploaded pixels. Choose Gemini or Ollama for real visual analysis. Model confidence is self-reported, and the 10-post metric evaluates only the labeled demo set, not newly uploaded images.

## Project notes

- [DESIGN.md](DESIGN.md) — data model, API, decision rules, and explicit non-goal.
- [EVIDENCE.md](EVIDENCE.md) — acceptance probe transcripts captured from the current build.
- [BUILDLOG.md](BUILDLOG.md) — AI assistance and ownership reflection.
- [capstone.yaml](capstone.yaml) — evaluator run, seed, evaluation command, and probe endpoints.
- [LICENSE](LICENSE) — MIT license; generated demo artwork is original to this project.
- `.env.example` — safe configuration template; never submit a populated `.env`.

## Public repository submission

The capstone brief requires a **dedicated public GitHub repository** named `flyrank-capstone-image-relevance`. This workspace's Git history contains a different earlier capstone, so do not present this repository history as satisfying that rule. Publish the finished source in a new dedicated public repository, add its remote, and submit that repository URL through the portal. Never upload a ZIP.
