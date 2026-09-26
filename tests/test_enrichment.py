from app.config import settings
from app.models import Submission
from tests.conftest import TEST_WIDGET_ID


def test_provider_a_answers_when_up(client, db_session):
    settings.mock_provider_a_up = True
    settings.mock_provider_b_up = True
    resp = client.post(
        "/submissions",
        json={"widget_id": TEST_WIDGET_ID, "fields": {"email": "a@example.com"}},
    )
    stored = db_session.get(Submission, resp.json()["id"])
    assert stored.geo_country == "Bangladesh"
    assert "via provider B" not in stored.geo_city


def test_falls_back_to_provider_b_when_a_is_down(client, db_session):
    """Probe 4, part 1: disable provider A -> the submission is still stored
    and enriched, this time by provider B."""
    settings.mock_provider_a_up = False
    settings.mock_provider_b_up = True
    try:
        resp = client.post(
            "/submissions",
            json={"widget_id": TEST_WIDGET_ID, "fields": {"email": "b@example.com"}},
        )
        assert resp.status_code == 201
        stored = db_session.get(Submission, resp.json()["id"])
        assert stored.geo_country == "Bangladesh"
        assert "via provider B" in stored.geo_city
    finally:
        settings.mock_provider_a_up = True  # don't leak state into other tests


def test_stores_without_geo_when_both_providers_down(client, db_session):
    """Probe 4, part 2: disable both providers -> submission still succeeds,
    just without geo data. Degrade, never fail."""
    settings.mock_provider_a_up = False
    settings.mock_provider_b_up = False
    try:
        resp = client.post(
            "/submissions",
            json={"widget_id": TEST_WIDGET_ID, "fields": {"email": "c@example.com"}},
        )
        assert resp.status_code == 201
        stored = db_session.get(Submission, resp.json()["id"])
        assert stored.geo_country is None
        assert stored.geo_city is None
    finally:
        settings.mock_provider_a_up = True
        settings.mock_provider_b_up = True
