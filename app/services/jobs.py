"""Retryable vision batch orchestration with persistent progress and cost attribution."""
import asyncio
import json
import time
import uuid

from app.config import settings
from app.db import db
from app.services.ai import AIProvider


def _call_log(meta: dict, operation: str, image_id: str, job_id: str, status: str, error: str | None = None, tenant_id: str = "demo"):
    with db.transaction() as conn:
        conn.execute("""INSERT INTO ai_calls
          (id,provider,operation,model,image_id,job_id,status,cost_usd,duration_ms,error,tenant_id)
          VALUES (?,?,?,?,?,?,?,?,?,?,?)""", (str(uuid.uuid4()), meta.get("provider", "unknown"), operation,
          meta.get("model", "unknown"), image_id, job_id, status, meta.get("cost_usd", 0),
          meta.get("duration_ms", 0), error, tenant_id))


async def run_vision_job(job_id: str, tenant_id: str = "demo"):
    with db.transaction() as conn:
        conn.execute("UPDATE jobs SET status='running',updated_at=CURRENT_TIMESTAMP WHERE id=? AND tenant_id=?", (job_id, tenant_id))
    images = db.rows("SELECT * FROM images WHERE tenant_id=? AND status IN ('pending','failed','processing') ORDER BY id", (tenant_id,))
    provider = AIProvider(tenant_id=tenant_id)
    for image in images:
        success = False
        for attempt in range(1, settings.batch_retries + 1):
            with db.transaction() as conn:
                conn.execute("UPDATE images SET status='processing',attempts=attempts+1,updated_at=CURRENT_TIMESTAMP WHERE id=? AND tenant_id=?", (image["id"], tenant_id))
                conn.execute("UPDATE jobs SET attempts=attempts+1,updated_at=CURRENT_TIMESTAMP WHERE id=? AND tenant_id=?", (job_id, tenant_id))
            try:
                image["attributes"] = json.loads(image.get("attributes_json") or "[]")
                tags, vision_meta = await provider.classify(image)
                _call_log(vision_meta, "vision", image["id"], job_id, "succeeded", tenant_id=tenant_id)
                vector, embed_meta = await provider.embed(tags.caption + " " + tags.subject + " " + " ".join(tags.attributes))
                _call_log(embed_meta, "image_embedding", image["id"], job_id, "succeeded", tenant_id=tenant_id)
                status = "needs_review" if tags.confidence < settings.min_confidence else "completed"
                with db.transaction() as conn:
                    conn.execute("""UPDATE images SET tags_json=?,vector_json=?,confidence=?,status=?,last_error=NULL,
                      updated_at=CURRENT_TIMESTAMP WHERE id=? AND tenant_id=?""", (tags.model_dump_json(), json.dumps(vector), tags.confidence, status, image["id"], tenant_id))
                # needs_review means processing succeeded; it is withheld by the guard.
                success = True
                break
            except Exception as exc:
                message = str(exc)[:1000]
                _call_log({"provider": provider.mode, "model": "vision", "cost_usd": 0, "duration_ms": 0}, "vision", image["id"], job_id, "failed", message, tenant_id)
                with db.transaction() as conn:
                    conn.execute("UPDATE images SET status='failed',last_error=?,updated_at=CURRENT_TIMESTAMP WHERE id=? AND tenant_id=?", (message, image["id"], tenant_id))
                if attempt < settings.batch_retries:
                    await asyncio.sleep(min(0.1 * (2 ** (attempt - 1)), 1.0))
        with db.transaction() as conn:
            conn.execute("""UPDATE jobs SET processed=processed+1,succeeded=succeeded+?,failed=failed+?,
              updated_at=CURRENT_TIMESTAMP WHERE id=? AND tenant_id=?""", (int(success), int(not success), job_id, tenant_id))
        if settings.batch_delay_seconds:
            await asyncio.sleep(settings.batch_delay_seconds)
    with db.transaction() as conn:
        conn.execute("UPDATE jobs SET status=CASE WHEN failed=0 THEN 'completed' ELSE 'completed_with_errors' END,finished_at=CURRENT_TIMESTAMP,updated_at=CURRENT_TIMESTAMP WHERE id=? AND tenant_id=?", (job_id, tenant_id))


def create_job(tenant_id: str = "demo") -> dict:
    job_id = str(uuid.uuid4())
    total = db.row("SELECT COUNT(*) AS n FROM images WHERE tenant_id=? AND status IN ('pending','failed','processing')", (tenant_id,))["n"]
    with db.transaction() as conn:
        conn.execute("INSERT INTO jobs(id,kind,status,total,tenant_id) VALUES (?, 'vision', 'queued', ?,?)", (job_id, total, tenant_id))
    return db.row("SELECT * FROM jobs WHERE id=? AND tenant_id=?", (job_id, tenant_id))
