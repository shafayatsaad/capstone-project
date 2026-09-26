from app.models import Submission, Widget
from tests.conftest import TEST_WIDGET_ID


def register(client, email):
    response = client.post("/auth/register", json={"email": email, "password": "correct-horse-42"})
    assert response.status_code == 201
    return {"Authorization": "Bearer " + response.json()["access_token"]}


def test_auth_and_widget_crud_are_tenant_scoped(client):
    headers_a = register(client, "owner-a@example.com")
    headers_b = register(client, "owner-b@example.com")
    payload = {"title": "A lead form", "fields": [{"name": "email", "label": "Email", "type": "email"}]}
    created = client.post("/widgets", json=payload, headers=headers_a)
    assert created.status_code == 201
    widget_id = created.json()["id"]
    assert client.get("/widgets", headers=headers_b).json() == []
    assert client.get(f"/widgets/{widget_id}", headers=headers_b).status_code == 404
    assert client.put(f"/widgets/{widget_id}", json=payload, headers=headers_b).status_code == 404
    assert client.delete(f"/widgets/{widget_id}", headers=headers_b).status_code == 404
    assert client.get("/widgets").status_code == 401


def test_widget_update_versions_embed_config_and_bundle_cache(client):
    headers = register(client, "delivery@example.com")
    created = client.post("/widgets", json={"title": "Join us", "fields": []}, headers=headers)
    widget = created.json()
    embed = client.get(f"/widgets/{widget['id']}/embed", headers=headers).json()
    assert f"v=1" in embed["snippet"]
    config = client.get(f"/widgets/{widget['id']}/config")
    assert config.status_code == 200
    assert config.headers["cache-control"].startswith("public, max-age=60")
    bundle = client.get("/widget.js?id=x&v=1")
    assert bundle.status_code == 200
    assert "immutable" in bundle.headers["cache-control"]
    updated = client.put(f"/widgets/{widget['id']}", json={"title": "Updated", "fields": []}, headers=headers)
    assert updated.json()["version"] == 2
    assert "v=2" in client.get(f"/widgets/{widget['id']}/embed", headers=headers).json()["snippet"]


def test_dashboard_only_returns_the_authenticated_owners_submissions(client, db_session):
    headers = register(client, "dashboard@example.com")
    other_headers = register(client, "other-dashboard@example.com")
    widget = client.post("/widgets", json={"title": "Dashboard form"}, headers=headers).json()
    accepted = client.post("/submissions", json={
        "widget_id": widget["id"], "fields": {"email": "lead@example.com"}
    })
    assert accepted.status_code == 201
    assert client.get("/dashboard/submissions").status_code == 401
    rows = client.get("/dashboard/submissions", headers=headers).json()["items"]
    assert [row["id"] for row in rows] == [accepted.json()["id"]]
    assert client.get("/dashboard/submissions", headers=other_headers).json()["items"] == []
    statistics = client.get("/dashboard/stats", headers=headers).json()
    assert statistics["total_submissions"] == 1
    assert statistics["per_widget"][0]["submissions"] == 1
    assert statistics["daily"][0]["submissions"] == 1


def test_idempotency_key_returns_the_original_submission(client, db_session):
    payload = {"widget_id": TEST_WIDGET_ID, "fields": {"email": "same@example.com"}}
    first = client.post("/submissions", json=payload, headers={"Idempotency-Key": "checkout-123"})
    again = client.post("/submissions", json=payload, headers={"Idempotency-Key": "checkout-123"})
    assert first.status_code == again.status_code == 201
    assert first.json()["id"] == again.json()["id"]
    assert db_session.query(Submission).filter_by(idempotency_key="checkout-123").count() == 1


def test_submission_checks_the_widget_field_contract(client):
    headers = register(client, "field-contract@example.com")
    widget = client.post("/widgets", json={
        "title": "Required email", "fields": [{"name": "email", "label": "Email", "type": "email", "required": True}]
    }, headers=headers).json()
    missing = client.post("/submissions", json={"widget_id": widget["id"], "fields": {}})
    unknown = client.post("/submissions", json={"widget_id": widget["id"], "fields": {"email": "a@example.com", "role": "admin"}})
    assert missing.status_code == 422
    assert "required" in missing.json()["detail"]
    assert unknown.status_code == 422
    assert "unknown field" in unknown.json()["detail"]
    invalid_email = client.post("/submissions", json={
        "widget_id": widget["id"], "fields": {"email": "not-an-email"}
    })
    assert invalid_email.status_code == 422
    assert "valid email" in invalid_email.json()["detail"]
