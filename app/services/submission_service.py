"""
The pipeline a public submission goes through, in order:

  1. widget must exist                          -> 404 if not
  2. widget-specific field contract              -> required/unknown checked
  3. honeypot check                              -> silently dropped with success shape
  4. geo enrichment (provider A -> B -> none)     -> never raises, never blocks
  5. store the row + durable notification outbox
  6. background notification retries             -> failure never changes the
                                                      stored submission response

Enrichment and notification delivery are best effort. Notification delivery
runs after the response through the persisted outbox worker.
"""
import logging
import re

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models import Submission
from app.repositories import submission_repo, widget_repo
from app.schemas import SubmissionCreate
from app.services import enrichment_service, spam_service

logger = logging.getLogger("submissions")


class WidgetNotFound(Exception):
    pass


class DuplicateSubmission(Exception):
    def __init__(self, submission: Submission):
        self.submission = submission


class SpamDropped(Exception):
    pass


class SubmissionInvalid(Exception):
    pass


def _validate_widget_fields(widget, values: dict[str, str]) -> None:
    definitions = widget.fields or []
    if not definitions:
        return
    by_name = {item.get("name"): item for item in definitions if item.get("name")}
    unknown = set(values) - set(by_name)
    if unknown:
        raise SubmissionInvalid(f"unknown field(s): {', '.join(sorted(unknown))}")
    for name, definition in by_name.items():
        value = values.get(name, "")
        if definition.get("required", False) and not value.strip():
            raise SubmissionInvalid(f"field '{name}' is required")
        if definition.get("type") == "email" and value and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            raise SubmissionInvalid(f"field '{name}' must be a valid email address")


async def create_submission(db: Session, payload: SubmissionCreate, client_ip: str) -> Submission:
    widget = widget_repo.get_widget(db, payload.widget_id)
    if widget is None:
        raise WidgetNotFound(payload.widget_id)

    _validate_widget_fields(widget, payload.fields)

    spam = spam_service.is_spam(payload)
    if spam:
        raise SpamDropped()

    if payload.idempotency_key:
        existing = db.query(Submission).filter(
            Submission.widget_id == payload.widget_id,
            Submission.idempotency_key == payload.idempotency_key,
        ).first()
        if existing is not None:
            raise DuplicateSubmission(existing)

    geo_country: str | None = None
    geo_city: str | None = None
    # Enrichment failures are already swallowed inside enrich(); this is
    # belt-and-braces so a future bug in that function can never take the
    # whole submission down.
    try:
        geo = await enrichment_service.enrich(client_ip)
        if geo:
            geo_country, geo_city = geo.country, geo.city
    except Exception:
        logger.exception("enrichment raised unexpectedly; storing without geo")

    try:
        submission = submission_repo.create_submission(
            db,
            widget_id=widget.id,
            data=payload.fields,
            ip_address=client_ip,
            geo_country=geo_country,
            geo_city=geo_city,
            is_spam=False,
            idempotency_key=payload.idempotency_key,
        )
    except IntegrityError:
        # A concurrent retry can win the unique-key race after our initial read.
        db.rollback()
        if payload.idempotency_key:
            existing = db.query(Submission).filter(
                Submission.widget_id == widget.id,
                Submission.idempotency_key == payload.idempotency_key,
            ).first()
            if existing is not None:
                raise DuplicateSubmission(existing)
        raise

    return submission
