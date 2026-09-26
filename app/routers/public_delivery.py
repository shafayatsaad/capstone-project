from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Widget

router = APIRouter(tags=["public-widget-delivery"])
_BUNDLE = Path(__file__).resolve().parents[2] / "static" / "widget.js"


@router.get("/widgets/{widget_id}/config")
def public_config(widget_id: str, db: Session = Depends(get_db)):
    widget = db.query(Widget).filter(Widget.id == widget_id).first()
    if widget is None:
        raise HTTPException(status_code=404, detail="widget not found")
    return Response(
        content=__import__("json").dumps({
            "id": widget.id, "type": widget.type, "title": widget.title,
            "description": widget.description, "fields": widget.fields or [],
            "button_text": widget.button_text, "display_options": widget.display_options or {},
            "version": widget.version,
        }),
        media_type="application/json",
        headers={"Cache-Control": "public, max-age=60, stale-while-revalidate=30"},
    )


@router.get("/widget.js")
def widget_bundle():
    if not _BUNDLE.exists():
        raise HTTPException(status_code=500, detail="widget bundle is missing")
    return Response(
        content=_BUNDLE.read_text(encoding="utf-8"),
        media_type="application/javascript",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )
