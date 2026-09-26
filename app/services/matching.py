"""Semantic retrieval, explicit mismatch guard, review, and labeled evaluation."""
import json
import re
import time
import uuid
from contextlib import nullcontext

from fastapi import HTTPException

from app.config import settings
from app.db import db
from app.services.ai import AIProvider, ProviderError
from app.services.embeddings import cosine


def _clean(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower().replace("vulpes vulpes", "fox").replace("canis lupus", "wolf")).strip()


def _category(value: str) -> str:
    cleaned = _clean(value)
    aliases = {"animal": "animals", "animals": "animals", "vehicle": "vehicles",
               "vehicles": "vehicles", "object": "objects", "objects": "objects",
               "food": "food", "nature": "nature", "landscape": "nature"}
    return aliases.get(cleaned, cleaned)


def _tags(image: dict) -> dict:
    try:
        return json.loads(image.get("tags_json") or "{}")
    except json.JSONDecodeError:
        return {}


def guard(post: dict, image: dict, similarity: float) -> tuple[str, str]:
    tags = _tags(image)
    if not tags:
        return "rejected", "Image classification is not ready for recommendation."
    if float(tags.get("confidence", 0)) < settings.min_confidence:
        return "rejected", f"Low vision confidence ({float(tags.get('confidence', 0)):.2f}); manual review required."
    if image["status"] != "completed":
        return "rejected", "Image classification is not ready for recommendation."
    expected_category = _category(post["expected_category"])
    actual_category = _category(tags.get("category", ""))
    if expected_category != actual_category:
        return "rejected", f"Category mismatch: expected {post['expected_category']}, detected {tags.get('category', 'unknown')}"
    expected = _clean(post["expected_subject"])
    detected = _clean(tags.get("subject", ""))
    if expected not in detected and detected not in expected:
        return "rejected", f"Subject mismatch: expected {post['expected_subject']}, detected {tags.get('subject', 'unknown')}"
    if similarity < settings.min_similarity:
        return "rejected", f"Similarity {similarity:.3f} is below the {settings.min_similarity:.2f} threshold."
    return "accepted", f"Subject and category agree; similarity {similarity:.3f} cleared the {settings.min_similarity:.2f} threshold."


async def match_post(post_id: str, force_image_id: str | None = None, tenant_id: str = "demo", persist: bool = True) -> dict:
    post = db.row("SELECT * FROM posts WHERE id=? AND tenant_id=?", (post_id, tenant_id))
    if not post:
        raise HTTPException(404, "Post not found")
    images = db.rows("SELECT * FROM images WHERE tenant_id=? AND status IN ('completed','needs_review')", (tenant_id,))
    if force_image_id:
        images = [image for image in images if image["id"] == force_image_id]
        if not images:
            # Return a clean result for an unknown or not-yet-classified image.
            raise HTTPException(404, "Candidate image not found or not classified")
    post_vector = json.loads(post["vector_json"]) if post.get("vector_json") else []
    ranked = []
    for image in images:
        vector = json.loads(image["vector_json"]) if image.get("vector_json") else []
        similarity = max(0.0, cosine(post_vector, vector))
        decision, reason = guard(post, image, similarity)
        ranked.append({"image": image, "similarity": similarity, "decision": decision, "reason": reason})
    ranked.sort(key=lambda row: (row["similarity"], row["image"]["id"]), reverse=True)
    results = []
    with (db.transaction() if persist else nullcontext()) as conn:
        for rank, item in enumerate(ranked, 1):
            suggestion_id = str(uuid.uuid4()) if persist else None
            image, tags = item["image"], _tags(item["image"])
            if persist:
                conn.execute("""INSERT INTO suggestions(id,post_id,image_id,similarity,confidence,decision,reason,rank,tenant_id)
                  VALUES (?,?,?,?,?,?,?,?,?)""", (suggestion_id, post_id, image["id"], item["similarity"], tags.get("confidence"), item["decision"], item["reason"], rank, tenant_id))
            media_path = image.get("image_url", "").removeprefix("data/images/")
            results.append({"id": suggestion_id, "image_id": image["id"], "image_url": f"/media/{media_path}", "title": image["title"],
              "category": tags.get("category"), "subject": tags.get("subject"), "caption": tags.get("caption"),
              "similarity": round(item["similarity"], 4), "confidence": tags.get("confidence"),
              "decision": item["decision"], "reason": item["reason"], "rank": rank, "review_status": "pending"})
    accepted = next((item for item in results if item["decision"] == "accepted"), None)
    if not accepted:
        reasons = list(dict.fromkeys(item["reason"] for item in results[:3]))
        if not reasons:
            reasons = ["No classified images are available; run the vision batch job first."]
        return {"post_id": post_id, "status": "no_confident_match", "suggestion": None, "candidates": results[:10], "reasons": reasons}
    return {"post_id": post_id, "status": "matched", "suggestion": accepted, "candidates": results[:10], "reasons": []}


async def create_post(data: dict, tenant_id: str = "demo") -> dict:
    provider = AIProvider(tenant_id=tenant_id)
    text = f"{data['title']} {data['body']} {data['expected_subject']} {data['expected_category']}"
    try:
        vector, meta = await provider.embed(text)
    except ProviderError as exc:
        raise HTTPException(503, f"Embedding provider unavailable: {exc}") from exc
    with db.transaction() as conn:
        post_id = str(uuid.uuid4())
        conn.execute("INSERT INTO posts(id,title,body,expected_category,expected_subject,vector_json,tenant_id) VALUES (?,?,?,?,?,?,?)",
          (post_id, data["title"], data["body"], data["expected_category"], data["expected_subject"], json.dumps(vector), tenant_id))
        conn.execute("""INSERT INTO ai_calls(id,provider,operation,model,post_id,status,input_tokens,output_tokens,cost_usd,duration_ms,tenant_id)
          VALUES (?,?,?,?,?,'succeeded',?,?,?,?,?)""", (str(uuid.uuid4()), meta["provider"], "post_embedding", meta["model"], post_id,
          meta.get("input_tokens", 0), meta.get("output_tokens", 0), meta["cost_usd"], meta["duration_ms"], tenant_id))
    return db.row("SELECT id,title,body,expected_category,expected_subject,created_at FROM posts WHERE id=? AND tenant_id=?", (post_id, tenant_id))


def review_suggestion(suggestion_id: str, decision: str, note: str = "", tenant_id: str = "demo") -> dict:
    row = db.row("SELECT * FROM suggestions WHERE id=? AND tenant_id=?", (suggestion_id, tenant_id))
    if not row:
        raise HTTPException(404, "Suggestion not found")
    with db.transaction() as conn:
        conn.execute("UPDATE suggestions SET review_status=?,reviewed_at=CURRENT_TIMESTAMP,reason=reason || ? WHERE id=? AND tenant_id=?",
          (decision, (" Reviewer note: " + note) if note else "", suggestion_id, tenant_id))
    return db.row("SELECT * FROM suggestions WHERE id=? AND tenant_id=?", (suggestion_id, tenant_id))


async def evaluate(tenant_id: str = "demo") -> dict:
    pending = db.row("SELECT COUNT(*) AS n FROM images WHERE tenant_id=? AND status IN ('pending','failed','processing')", (tenant_id,))["n"]
    if pending:
        from app.services.jobs import create_job, run_vision_job
        job = create_job(tenant_id)
        await run_vision_job(job["id"], tenant_id)
        state = db.row("SELECT status,failed FROM jobs WHERE id=? AND tenant_id=?", (job["id"], tenant_id))
        if state["status"] == "completed_with_errors":
            raise HTTPException(503, f"Cannot evaluate; vision batch has {state['failed']} failed images")
    eval_path = "data/eval_set.json"
    if tenant_id != "demo":
        raise HTTPException(404, "No labeled evaluation set is configured for this tenant")
    with open(eval_path, encoding="utf-8") as handle:
        cases = json.load(handle)
    rows = []
    correct = 0
    for case in cases:
        result = await match_post(case["post_id"], tenant_id=tenant_id, persist=False)
        top = result.get("suggestion")
        hit = bool(top and top["image_id"] == case["expected_image_id"])
        correct += int(hit)
        rows.append({"post_id": case["post_id"], "expected_image_id": case["expected_image_id"],
                     "top_image_id": top["image_id"] if top else None, "correct": hit})
    result = {"cases": len(cases), "correct": correct, "top1_precision": round(correct / len(cases), 4) if cases else 0.0, "results": rows}
    with db.transaction() as conn:
        conn.execute("""INSERT INTO evaluation_runs(id,tenant_id,cases,correct,top1_precision,results_json)
          VALUES (?,?,?,?,?,?)""", (str(uuid.uuid4()), tenant_id, result["cases"], result["correct"], result["top1_precision"], json.dumps(rows)))
    return result


def latest_evaluation(tenant_id: str = "demo") -> dict:
    run = db.row("SELECT * FROM evaluation_runs WHERE tenant_id=? ORDER BY created_at DESC,rowid DESC LIMIT 1", (tenant_id,))
    if not run:
        return {"available": False}
    return {"available": True, "cases": run["cases"], "correct": run["correct"],
            "top1_precision": run["top1_precision"], "results": json.loads(run["results_json"]), "created_at": run["created_at"]}
