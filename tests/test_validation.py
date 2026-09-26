import json

from app.config import settings
from tests.conftest import TEST_WIDGET_ID


def test_valid_submission_is_stored_and_returns_201(client):
    resp = client.post(
        "/submissions",
        json={"widget_id": TEST_WIDGET_ID, "fields": {"email": "visitor@example.com"}},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["widget_id"] == TEST_WIDGET_ID
    assert "id" in body
    # internal fields are never echoed to the public caller
    assert "is_spam" not in body
    assert "ip_address" not in body


def test_missing_widget_returns_404_not_500(client):
    resp = client.post(
        "/submissions",
        json={"widget_id": "does-not-exist", "fields": {"email": "x@example.com"}},
    )
    assert resp.status_code == 404


def test_malformed_payload_returns_422_not_500(client):
    # widget_id missing entirely
    resp = client.post("/submissions", json={"fields": {"email": "x@example.com"}})
    assert resp.status_code == 422


def test_too_many_fields_returns_422(client):
    too_many = {f"field_{i}": "x" for i in range(settings.max_fields + 1)}
    resp = client.post("/submissions", json={"widget_id": TEST_WIDGET_ID, "fields": too_many})
    assert resp.status_code == 422


def test_oversized_payload_returns_413_not_500(client):
    huge_value = "x" * (settings.max_payload_bytes + 1)
    raw_body = json.dumps({"widget_id": TEST_WIDGET_ID, "fields": {"note": huge_value}})
    resp = client.post(
        "/submissions",
        content=raw_body.encode(),
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 413
