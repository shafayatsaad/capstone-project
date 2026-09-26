import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.rate_limit import limiter
from app.schemas import SubmissionCreate, SubmissionOut
from app.services import submission_service
from app.services.submission_service import WidgetNotFound

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
async def submit(request: Request, db: Session = Depends(get_db)):
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
        raise HTTPException(status_code=422, detail=exc.errors())

    client_ip = request.client.host if request.client else "unknown"

    try:
        submission = await submission_service.create_submission(db, payload, client_ip)
    except WidgetNotFound:
        raise HTTPException(status_code=404, detail="widget not found")

    return submission
