from typing import Optional

from sqlalchemy.orm import Session

from app.models import Widget


def get_widget(db: Session, widget_id: str) -> Optional[Widget]:
    """Deliberately unscoped by owner: this is used from the *public* delivery
    and submission paths, which don't have an authenticated owner in context.
    Owner-scoped lookups for the admin API belong in Phase 3 and must always
    filter by owner_id -- see DESIGN.md's tenant isolation rule."""
    return db.query(Widget).filter(Widget.id == widget_id).first()
