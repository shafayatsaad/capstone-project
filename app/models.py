import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, Integer, JSON, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Owner(Base):
    """The authenticated tenant / customer account that owns widgets."""
    __tablename__ = "owners"

    id = Column(String, primary_key=True, default=_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now)

    widgets = relationship("Widget", back_populates="owner", cascade="all, delete-orphan")


class Widget(Base):
    __tablename__ = "widgets"

    id = Column(String, primary_key=True, default=_uuid)
    owner_id = Column(String, ForeignKey("owners.id"), nullable=False, index=True)
    type = Column(String, nullable=False, default="signup_form")  # signup_form | cta | popover
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    fields = Column(JSON, default=list)  # [{"name": "email", "label": "Email", "type": "email", "required": true}]
    button_text = Column(String, default="Submit")
    display_options = Column(JSON, default=dict)
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    owner = relationship("Owner", back_populates="widgets")
    submissions = relationship("Submission", back_populates="widget", cascade="all, delete-orphan")


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(String, primary_key=True, default=_uuid)
    widget_id = Column(String, ForeignKey("widgets.id"), nullable=False, index=True)
    data = Column(JSON, nullable=False)
    ip_address = Column(String, nullable=False)
    geo_country = Column(String, nullable=True)
    geo_city = Column(String, nullable=True)
    is_spam = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now, index=True)
    idempotency_key = Column(String(128), nullable=True)

    widget = relationship("Widget", back_populates="submissions")

    __table_args__ = (UniqueConstraint("widget_id", "idempotency_key", name="uq_submission_widget_idempotency"),)


class NotificationJob(Base):
    """Durable outbox record for the confirmation side effect."""
    __tablename__ = "notification_jobs"

    id = Column(String, primary_key=True, default=_uuid)
    submission_id = Column(String, ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    widget_id = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending", index=True)
    attempts = Column(Integer, nullable=False, default=0)
    next_retry_at = Column(DateTime(timezone=True), default=_now, nullable=False, index=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)
