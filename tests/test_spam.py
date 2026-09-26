from app.models import Submission
from tests.conftest import TEST_WIDGET_ID


def test_honeypot_fill_is_flagged_spam_but_still_looks_like_success(client, db_session):
    """A bot that fills every field (including the hidden honeypot) gets an
    ordinary-looking 201 -- it isn't told it was caught -- but the row is
    flagged is_spam=True so the owner's dashboard can filter it out."""
    resp = client.post(
        "/submissions",
        json={
            "widget_id": TEST_WIDGET_ID,
            "fields": {"email": "bot@example.com"},
            "hp_field": "I am a bot and I filled this",
        },
    )
    assert resp.status_code == 201
    submission_id = resp.json()["id"]

    stored = db_session.get(Submission, submission_id)
    assert stored.is_spam is True
    # spam submissions skip enrichment entirely
    assert stored.geo_country is None


def test_real_visitor_leaves_honeypot_empty(client, db_session):
    resp = client.post(
        "/submissions",
        json={"widget_id": TEST_WIDGET_ID, "fields": {"email": "visitor@example.com"}},
    )
    assert resp.status_code == 201
    stored = db_session.get(Submission, resp.json()["id"])
    assert stored.is_spam is False
