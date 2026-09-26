from tests.conftest import TEST_WIDGET_ID


def test_cross_origin_submission_is_accepted(client):
    """Simulates the customer-site -> API call: a different Origin header,
    same as a real cross-origin browser request would send."""
    resp = client.post(
        "/submissions",
        json={"widget_id": TEST_WIDGET_ID, "fields": {"email": "visitor@example.com"}},
        headers={"Origin": "http://localhost:5500"},
    )
    assert resp.status_code == 201
    assert resp.headers.get("access-control-allow-origin") in ("*", "http://localhost:5500")


def test_preflight_options_request_is_handled(client):
    resp = client.options(
        "/submissions",
        headers={
            "Origin": "http://localhost:5500",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert resp.status_code == 200
    assert "access-control-allow-origin" in resp.headers
    assert "POST" in resp.headers.get("access-control-allow-methods", "")
