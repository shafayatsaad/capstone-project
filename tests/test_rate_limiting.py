from tests.conftest import TEST_WIDGET_ID

# RATE_LIMIT_SUBMISSIONS is set to "3/minute" in conftest.py specifically so
# this test can trip it without sending dozens of requests.


def test_burst_of_requests_returns_429_then_recovers(client):
    """Probe 3: a burst trips the limiter (429s appear), and the service
    itself keeps running -- it isn't a crash, just a rejection."""
    statuses = []
    for i in range(5):
        resp = client.post(
            "/submissions",
            json={"widget_id": TEST_WIDGET_ID, "fields": {"email": f"burst{i}@example.com"}},
        )
        statuses.append(resp.status_code)

    assert 201 in statuses, "at least the first requests under the limit should succeed"
    assert 429 in statuses, "requests over the limit should be rejected with 429"

    # the limit is per-IP; a different, unrelated request path must still work
    health = client.get("/health")
    assert health.status_code == 200
