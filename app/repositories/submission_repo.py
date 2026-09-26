from typing import Optional

from sqlalchemy.orm import Session

from app.models import Submission


def create_submission(
    db: Session,
    *,
    widget_id: str,
    data: dict,
    ip_address: str,
    geo_country: Optional[str],
    geo_city: Optional[str],
    is_spam: bool,
) -> Submission:
    submission = Submission(
        widget_id=widget_id,
        data=data,
        ip_address=ip_address,
        geo_country=geo_country,
        geo_city=geo_city,
        is_spam=is_spam,
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return submission
