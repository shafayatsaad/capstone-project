from app.config import settings
from tests.conftest import TEST_WIDGET_ID


def test_failing_notify_side_effect_does_not_break_submission(client):
    """Probe 5: force the confirmation-email/webhook side effect to throw ->
    the submission must still return success and still be stored."""
    settings.force_notify_fail = True
    try:
        resp = client.post(
            "/submissions",
            json={"widget_id": TEST_WIDGET_ID, "fields": {"email": "d@example.com"}},
        )
        assert resp.status_code == 201
        assert "id" in resp.json()
    finally:
        settings.force_notify_fail = False
