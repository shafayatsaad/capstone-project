"""FastAPI entry point for the AI image matching capstone."""
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.db import db
from app.config import settings
from app.schemas import PostInput, ReviewInput
from app.services.jobs import create_job, run_vision_job
from app.services.matching import create_post, evaluate, match_post, review_suggestion

app = FastAPI(title="AI Image Understanding & Content Matching Engine", version="1.0.0",
              description="Classify a small image library, rank article matches, and refuse unsafe suggestions.")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"], allow_headers=["*"])
app.mount("/media", StaticFiles(directory="data/images", check_dir=False), name="media")
app.mount("/demo", StaticFiles(directory="static/demo", check_dir=False), name="demo")


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
        row["image_url"] = f"/media/{row['id']}.png"
        row.pop("vector_json", None); row.pop("attributes_json", None)
    return {"items": rows, "count": len(rows)}


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
