from typing import Optional

from sqlalchemy.orm import Session

from app.models import Widget


def get_widget(db: Session, widget_id: str) -> Optional[Widget]:
    """Unscoped lookup for public delivery/submission paths only.

    Owner-facing lookups use the authenticated owner_id in app.routers.widgets.
    """
    return db.query(Widget).filter(Widget.id == widget_id).first()
