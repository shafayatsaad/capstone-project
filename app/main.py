"""FastAPI entry point for the AI image matching capstone."""
from fastapi import BackgroundTasks, FastAPI, File, Form, Header, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import json
import uuid
import hashlib
import warnings
from PIL import Image, UnidentifiedImageError

from app.db import db
from app.config import settings
from app.schemas import PostInput, ReviewInput
from app.services.jobs import create_job, run_vision_job
from app.services.matching import create_post, evaluate, latest_evaluation, match_post, review_suggestion

app = FastAPI(title="AI Image Understanding & Content Matching Engine", version="1.0.0",
              description="Classify a small image library, rank article matches, and refuse unsafe suggestions.")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"], allow_headers=["*"])
app.mount("/media", StaticFiles(directory="data/images", check_dir=False), name="media")
app.mount("/demo", StaticFiles(directory="static/demo", check_dir=False), name="demo")

IMAGE_ROOT = Path("data/images").resolve()
ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}


@app.on_event("startup")
def recover_interrupted_jobs():
    # Processing is restart-safe: a killed process leaves rows retryable.
    with db.transaction() as conn:
        conn.execute("UPDATE images SET status='failed',last_error='Previous process stopped during classification' WHERE status='processing'")
        conn.execute("UPDATE jobs SET status='failed',last_error='Previous process stopped during classification',finished_at=CURRENT_TIMESTAMP,updated_at=CURRENT_TIMESTAMP WHERE status IN ('queued','running')")


@app.get("/")
def home():
    return FileResponse(Path("static/demo/index.html"))


@app.get("/health")
def health():
    return {"status": "ok", "provider": settings.ai_provider}


@app.get("/images")
def list_images(status: str | None = Query(default=None), limit: int = Query(default=100, ge=1, le=500), tenant_id: str = Header(default="demo", alias="X-Tenant-ID", min_length=1, max_length=80)):
    sql, args = "SELECT * FROM images WHERE tenant_id=?", [tenant_id]
    if status:
        if status not in {"pending", "processing", "completed", "needs_review", "failed"}:
            raise HTTPException(422, "Unsupported image status")
        sql += " AND status=?"; args.append(status)
    sql += " ORDER BY id LIMIT ?"; args.append(limit)
    rows = db.rows(sql, tuple(args))
    import json
    for row in rows:
        row["tags"] = json.loads(row.pop("tags_json")) if row.get("tags_json") else None
        row["image_url"] = "/media/" + row["image_url"].removeprefix("data/images/")
        row.pop("vector_json", None); row.pop("attributes_json", None)
    return {"items": rows, "count": len(rows)}


@app.post("/images", status_code=201)
async def upload_image(
    file: UploadFile = File(...),
    title: str = Form(default=""),
    category: str = Form(default=""),
    subject_hint: str = Form(default=""),
    tenant_id: str = Header(default="demo", alias="X-Tenant-ID", min_length=1, max_length=80),
):
    """Upload a validated image into this workspace; classification is started separately."""
    if file.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(415, "Upload a JPG, PNG, or WebP image")
    raw = await file.read(settings.upload_max_bytes + 1)
    await file.close()
    if not raw or len(raw) > settings.upload_max_bytes:
        raise HTTPException(413, f"Image must be non-empty and at most {settings.upload_max_bytes // (1024*1024)} MB")
    try:
        import io
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as probe:
                if probe.format not in ALLOWED_IMAGE_FORMATS:
                    raise HTTPException(415, "Image content must be JPG, PNG, or WebP")
                if probe.width * probe.height > 25_000_000:
                    raise HTTPException(413, "Image dimensions exceed the 25-megapixel safety limit")
                probe.verify()
            with Image.open(io.BytesIO(raw)) as source:
                source.load()
                source = source.convert("RGB")
                source.thumbnail((1800, 1800), Image.Resampling.LANCZOS)
                image_id = "upload-" + uuid.uuid4().hex
                tenant_folder = hashlib.sha256(tenant_id.encode("utf-8")).hexdigest()[:16]
                relative_path = Path("uploads") / tenant_folder / f"{image_id}.jpg"
                target = IMAGE_ROOT / relative_path
                target.parent.mkdir(parents=True, exist_ok=True)
                source.save(target, format="JPEG", quality=88, optimize=True)
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise HTTPException(422, "The uploaded file is not a safe, readable image") from exc
    clean_title = title.strip()[:180] or Path(file.filename or "Uploaded image").stem[:180]
    clean_category = category.strip()[:40] or "uncategorized"
    clean_subject = subject_hint.strip()[:80] or "uploaded image"
    caption = (f"User-provided demo label for {clean_subject}" if subject_hint.strip()
               else "Uploaded image awaiting real vision classification")
    # In offline demo mode these are explicit user hints; low-confidence uploads
    # without a subject hint remain withheld for human review.
    confidence = 0.75 if subject_hint.strip() else 0.30
    with db.transaction() as conn:
        conn.execute("""INSERT INTO images(id,title,category,expected_subject,caption_hint,attributes_json,
          demo_confidence,image_url,source,status,tenant_id) VALUES (?,?,?,?,?,?,?,?,?,'pending',?)""",
          (image_id, clean_title, clean_category, clean_subject, caption, json.dumps([]), confidence,
           (Path("data/images") / relative_path).as_posix(), "user-upload", tenant_id))
    return {"id": image_id, "title": clean_title, "image_url": f"/media/{relative_path.as_posix()}",
            "status": "pending", "source": "user-upload", "provider": settings.ai_provider,
            "note": "Run the vision batch. Demo mode uses supplied label hints; choose Gemini, NVIDIA, or Ollama for visual analysis."}


@app.post("/jobs/vision", status_code=202)
def start_vision_job(background_tasks: BackgroundTasks, tenant_id: str = Header(default="demo", alias="X-Tenant-ID", min_length=1, max_length=80)):
    active = db.row("SELECT id FROM jobs WHERE tenant_id=? AND kind='vision' AND status IN ('queued','running') LIMIT 1", (tenant_id,))
    if active:
        raise HTTPException(409, f"Vision job {active['id']} is already active")
    job = create_job(tenant_id)
    background_tasks.add_task(run_vision_job, job["id"], tenant_id)
    return job


@app.get("/jobs/{job_id}")
def get_job(job_id: str, tenant_id: str = Header(default="demo", alias="X-Tenant-ID", min_length=1, max_length=80)):
    job = db.row("SELECT * FROM jobs WHERE id=? AND tenant_id=?", (job_id, tenant_id))
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@app.get("/posts")
def list_posts(tenant_id: str = Header(default="demo", alias="X-Tenant-ID", min_length=1, max_length=80)):
    return {"items": db.rows("SELECT id,title,body,expected_category,expected_subject,created_at FROM posts WHERE tenant_id=? ORDER BY id", (tenant_id,))}


@app.post("/posts", status_code=201)
async def add_post(data: PostInput, tenant_id: str = Header(default="demo", alias="X-Tenant-ID", min_length=1, max_length=80)):
    return await create_post(data.model_dump(), tenant_id)


@app.get("/posts/{post_id}/images")
async def post_images(post_id: str, force_image_id: str | None = None, tenant_id: str = Header(default="demo", alias="X-Tenant-ID", min_length=1, max_length=80)):
    return await match_post(post_id, force_image_id, tenant_id)


@app.post("/suggestions/{suggestion_id}/review")
def review(suggestion_id: str, data: ReviewInput, tenant_id: str = Header(default="demo", alias="X-Tenant-ID", min_length=1, max_length=80)):
    result = review_suggestion(suggestion_id, data.decision, data.note, tenant_id)
    return {"id": result["id"], "decision": data.decision, "review_status": result["review_status"], "reason": result["reason"]}


@app.get("/costs")
def costs(tenant_id: str = Header(default="demo", alias="X-Tenant-ID", min_length=1, max_length=80)):
    totals = db.row("SELECT COUNT(*) AS calls,COALESCE(SUM(cost_usd),0) AS total_cost_usd FROM ai_calls WHERE tenant_id=?", (tenant_id,))
    by_operation = db.rows("SELECT operation,provider,model,COUNT(*) AS calls,ROUND(SUM(cost_usd),6) AS cost_usd FROM ai_calls WHERE tenant_id=? GROUP BY operation,provider,model ORDER BY operation", (tenant_id,))
    calls = db.rows("SELECT id,provider,operation,model,image_id,post_id,job_id,status,cost_usd,duration_ms,error,created_at FROM ai_calls WHERE tenant_id=? ORDER BY created_at DESC LIMIT 200", (tenant_id,))
    from app.config import settings
    return {**totals, "total_cost_usd": round(totals["total_cost_usd"], 6), "budget_usd": settings.cost_budget_usd,
            "budget_remaining_usd": round(max(0, settings.cost_budget_usd-totals["total_cost_usd"]),6), "by_operation": by_operation, "calls": calls}


@app.post("/eval/run")
async def run_eval(tenant_id: str = Header(default="demo", alias="X-Tenant-ID", min_length=1, max_length=80)):
    return await evaluate(tenant_id)


@app.get("/eval/latest")
def get_latest_eval(tenant_id: str = Header(default="demo", alias="X-Tenant-ID", min_length=1, max_length=80)):
    return latest_evaluation(tenant_id)
