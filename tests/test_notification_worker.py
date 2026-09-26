from app.config import settings
from app.models import NotificationJob, Submission
from app.services.notification_worker import deliver_notification
from tests.conftest import TEST_WIDGET_ID


def test_failed_notification_retries_and_keeps_submission_successful(client, db_session):
    settings.force_notify_fail = True
    try:
        response = client.post("/submissions", json={
            "widget_id": TEST_WIDGET_ID, "fields": {"email": "outbox@example.com"}
        })
        assert response.status_code == 201
        submission_id = response.json()["id"]
        stored = db_session.get(Submission, submission_id)
        job = db_session.query(NotificationJob).filter_by(submission_id=submission_id).one()
        assert stored is not None
        assert job.status == "failed"
        assert job.attempts == 3
        assert job.last_error
    finally:
        settings.force_notify_fail = False


def test_notification_worker_marks_successful_job_sent(client, db_session):
    response = client.post("/submissions", json={
        "widget_id": TEST_WIDGET_ID, "fields": {"email": "sent@example.com"}
    })
    job = db_session.query(NotificationJob).filter_by(submission_id=response.json()["id"]).one()
    assert job.status == "sent"
    assert job.attempts == 1
