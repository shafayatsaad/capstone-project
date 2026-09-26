from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Owner, Submission, Widget
from app.security import current_owner
from app.routers.widgets import _owned_widget

router = APIRouter(prefix="/dashboard", tags=["owner-dashboard"])


@router.get("/submissions")
def submissions(
    widget_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    owner: Owner = Depends(current_owner), db: Session = Depends(get_db),
):
    query = db.query(Submission).join(Widget).filter(Widget.owner_id == owner.id, Submission.is_spam.is_(False))
    if widget_id:
        _owned_widget(db, widget_id, owner.id)
        query = query.filter(Submission.widget_id == widget_id)
    rows = query.order_by(Submission.created_at.desc()).offset(offset).limit(limit).all()
    return {"items": [{"id": r.id, "widget_id": r.widget_id, "data": r.data, "geo_country": r.geo_country,
                       "geo_city": r.geo_city, "created_at": r.created_at} for r in rows], "limit": limit, "offset": offset}


@router.get("/stats")
def stats(
    days: int = Query(default=30, ge=1, le=365),
    widget_id: str | None = None,
    owner: Owner = Depends(current_owner), db: Session = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    base = db.query(Submission).join(Widget).filter(
        Widget.owner_id == owner.id, Submission.is_spam.is_(False), Submission.created_at >= since
    )
    if widget_id:
        _owned_widget(db, widget_id, owner.id)
        base = base.filter(Submission.widget_id == widget_id)
    total = base.count()
    per_widget = db.query(Submission.widget_id, func.count(Submission.id)).join(Widget).filter(
        Widget.owner_id == owner.id, Submission.is_spam.is_(False), Submission.created_at >= since
    )
    if widget_id:
        per_widget = per_widget.filter(Submission.widget_id == widget_id)
    per_widget = per_widget.group_by(Submission.widget_id).all()
    daily = db.query(func.date(Submission.created_at), func.count(Submission.id)).join(Widget).filter(
        Widget.owner_id == owner.id, Submission.is_spam.is_(False), Submission.created_at >= since
    )
    if widget_id:
        daily = daily.filter(Submission.widget_id == widget_id)
    daily = daily.group_by(func.date(Submission.created_at)).order_by(func.date(Submission.created_at)).all()
    geo = db.query(Submission.geo_country, func.count(Submission.id)).join(Widget).filter(
        Widget.owner_id == owner.id, Submission.is_spam.is_(False), Submission.created_at >= since,
        Submission.geo_country.isnot(None),
    )
    if widget_id:
        geo = geo.filter(Submission.widget_id == widget_id)
    return {"days": days, "total_submissions": total,
            "daily": [{"date": day.isoformat() if hasattr(day, "isoformat") else str(day), "submissions": count}
                      for day, count in daily],
            "per_widget": [{"widget_id": key, "submissions": count} for key, count in per_widget],
            "geo_breakdown": [{"country": country, "submissions": count} for country, count in geo.group_by(Submission.geo_country).all()]}
