from typing import Optional

from sqlalchemy.orm import Session

from app.models import NotificationJob, Submission


def create_submission(
    db: Session,
    *,
    widget_id: str,
    data: dict,
    ip_address: str,
    geo_country: Optional[str],
    geo_city: Optional[str],
    is_spam: bool,
    idempotency_key: Optional[str] = None,
) -> Submission:
    submission = Submission(
        widget_id=widget_id,
        data=data,
        ip_address=ip_address,
        geo_country=geo_country,
        geo_city=geo_city,
        is_spam=is_spam,
        idempotency_key=idempotency_key,
    )
    db.add(submission)
    db.flush()
    if not is_spam:
        db.add(NotificationJob(submission_id=submission.id, widget_id=widget_id))
    db.commit()
    db.refresh(submission)
    return submission
