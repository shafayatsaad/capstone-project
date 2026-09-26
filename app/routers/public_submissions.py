import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.rate_limit import limiter
from app.schemas import SubmissionCreate, SubmissionOut
from app.services import submission_service
from app.services.submission_service import WidgetNotFound
from app.services.submission_service import DuplicateSubmission, SpamDropped
from app.services.submission_service import SubmissionInvalid
from app.services.notification_worker import deliver_notification

router = APIRouter(tags=["public-submissions"])
logger = logging.getLogger("public_submissions")


@router.post(
    "/submissions",
    status_code=201,
    response_model=SubmissionOut,
    responses={
        404: {"description": "widget does not exist"},
        413: {"description": "payload too large"},
        422: {"description": "payload failed validation"},
        429: {"description": "rate limit exceeded"},
    },
)
@limiter.limit(settings.rate_limit_submissions)
async def submit(
    request: Request,
    background_tasks: BackgroundTasks,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", max_length=128),
    db: Session = Depends(get_db),
):
    """
    The one endpoint on the open internet. Order matters:
    size check -> parse/validate -> widget lookup -> spam/enrichment/store/notify
    (the last four happen inside submission_service). Nothing here ever returns
    a 500 for bad input -- only for a genuine server bug.
    """
    body = await request.body()
    if len(body) > settings.max_payload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"payload exceeds {settings.max_payload_bytes} bytes",
        )

    try:
        payload = SubmissionCreate.model_validate_json(body)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors(include_context=False, include_url=False))

    client_ip = request.client.host if request.client else "unknown"
    if idempotency_key:
        payload.idempotency_key = idempotency_key

    try:
        submission = await submission_service.create_submission(db, payload, client_ip)
    except DuplicateSubmission as duplicate:
        return duplicate.submission
    except SpamDropped:
        # A bot receives the same shape and success status, but nothing is stored.
        return {"id": str(uuid.uuid4()), "widget_id": payload.widget_id, "created_at": datetime.now(timezone.utc)}
    except WidgetNotFound:
        raise HTTPException(status_code=404, detail="widget not found")
    except SubmissionInvalid as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    background_tasks.add_task(deliver_notification, submission.id)

    return submission
