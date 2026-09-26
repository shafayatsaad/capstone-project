from app.models import Submission
from tests.conftest import TEST_WIDGET_ID


def test_honeypot_fill_is_silently_dropped(client, db_session):
    """A bot gets the ordinary success shape, but no spam row is persisted."""
    resp = client.post(
        "/submissions",
        json={
            "widget_id": TEST_WIDGET_ID,
            "fields": {"email": "bot@example.com"},
            "hp_field": "I am a bot and I filled this",
        },
    )
    assert resp.status_code == 201
    assert db_session.query(Submission).filter(
        Submission.widget_id == TEST_WIDGET_ID,
        Submission.data["email"].as_string() == "bot@example.com",
    ).count() == 0


def test_real_visitor_leaves_honeypot_empty(client, db_session):
    resp = client.post(
        "/submissions",
        json={"widget_id": TEST_WIDGET_ID, "fields": {"email": "visitor@example.com"}},
    )
    assert resp.status_code == 201
    stored = db_session.get(Submission, resp.json()["id"])
    assert stored.is_spam is False
