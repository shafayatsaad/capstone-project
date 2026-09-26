"""Durable outbox worker. Background delivery retries; failed jobs remain inspectable."""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from app.db import SessionLocal
from app.models import NotificationJob
from app.services.notify_service import send_confirmation

logger = logging.getLogger("notification_worker")
MAX_ATTEMPTS = 3


async def deliver_notification(submission_id: str) -> None:
    for attempt in range(1, MAX_ATTEMPTS + 1):
        db = SessionLocal()
        job = db.query(NotificationJob).filter(NotificationJob.submission_id == submission_id).first()
        if job is None or job.status == "sent":
            db.close()
            return
        job.attempts = attempt
        try:
            await send_confirmation(job.submission_id, job.widget_id)
            job.status = "sent"
            job.last_error = None
            db.commit()
            db.close()
            return
        except Exception as exc:
            job.last_error = str(exc)[:1000]
            if attempt == MAX_ATTEMPTS:
                job.status = "failed"
                logger.exception("ALERT: notification exhausted retries for submission=%s", submission_id)
            else:
                job.status = "pending"
                job.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=2 ** (attempt - 1))
            db.commit()
            db.close()
            if attempt < MAX_ATTEMPTS:
                await asyncio.sleep(0.1 * (2 ** (attempt - 1)))


def retry_due_jobs(limit: int = 100) -> int:
    """Worker entry point for scheduled recovery of pending durable outbox jobs."""
    db = SessionLocal()
    now = datetime.now(timezone.utc)
    jobs = db.query(NotificationJob).filter(
        NotificationJob.status == "pending", NotificationJob.next_retry_at <= now
    ).order_by(NotificationJob.created_at).limit(limit).all()
    ids = [job.submission_id for job in jobs]
    db.close()
    for submission_id in ids:
        asyncio.run(deliver_notification(submission_id))
    return len(ids)
