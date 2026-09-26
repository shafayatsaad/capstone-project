from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import NotificationJob, Owner, Submission, Widget
from app.schemas import WidgetCreate, WidgetOut, WidgetUpdate
from app.security import current_owner

router = APIRouter(prefix="/widgets", tags=["widget-management"])


def _owned_widget(db: Session, widget_id: str, owner_id: str) -> Widget:
    widget = db.query(Widget).filter(Widget.id == widget_id, Widget.owner_id == owner_id).first()
    if widget is None:
        raise HTTPException(status_code=404, detail="widget not found")
    return widget


@router.post("", status_code=201, response_model=WidgetOut)
def create_widget(payload: WidgetCreate, owner: Owner = Depends(current_owner), db: Session = Depends(get_db)):
    widget = Widget(owner_id=owner.id, **payload.model_dump())
    db.add(widget)
    db.commit()
    db.refresh(widget)
    return widget


@router.get("", response_model=list[WidgetOut])
def list_widgets(owner: Owner = Depends(current_owner), db: Session = Depends(get_db)):
    return db.query(Widget).filter(Widget.owner_id == owner.id).order_by(Widget.created_at.desc()).all()


@router.get("/{widget_id}", response_model=WidgetOut)
def get_widget(widget_id: str, owner: Owner = Depends(current_owner), db: Session = Depends(get_db)):
    return _owned_widget(db, widget_id, owner.id)


@router.put("/{widget_id}", response_model=WidgetOut)
def update_widget(widget_id: str, payload: WidgetUpdate, owner: Owner = Depends(current_owner), db: Session = Depends(get_db)):
    widget = _owned_widget(db, widget_id, owner.id)
    for key, value in payload.model_dump().items():
        setattr(widget, key, value)
    widget.version += 1
    db.commit()
    db.refresh(widget)
    return widget


@router.delete("/{widget_id}", status_code=204)
def delete_widget(widget_id: str, owner: Owner = Depends(current_owner), db: Session = Depends(get_db)):
    widget = _owned_widget(db, widget_id, owner.id)
    submission_ids = db.query(Submission.id).filter(Submission.widget_id == widget.id).subquery()
    db.query(NotificationJob).filter(NotificationJob.submission_id.in_(submission_ids)).delete(synchronize_session=False)
    db.query(Submission).filter(Submission.widget_id == widget.id).delete(synchronize_session=False)
    db.delete(widget)
    db.commit()
    return Response(status_code=204)


@router.get("/{widget_id}/embed")
def embed_snippet(widget_id: str, owner: Owner = Depends(current_owner), db: Session = Depends(get_db)):
    widget = _owned_widget(db, widget_id, owner.id)
    src = f"{settings.public_base_url.rstrip('/')}/widget.js?id={widget.id}&v={widget.version}"
    return {"widget_id": widget.id, "version": widget.version, "snippet": f'<script async src="{src}"></script>'}
