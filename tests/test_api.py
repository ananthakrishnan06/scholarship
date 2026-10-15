import pytest
from core.corpus import records
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return APIClient()


def test_removed_profile_routes_and_preserved_scholarship_data(client):
    assert client.post("/api/profile/validate", {}, format="json").status_code == 404
    assert client.post("/api/eligibility/check", {"profile": {}}, format="json").status_code == 404
    search = client.post("/api/scholarships/search", {"category": "OBC"}, format="json")
    assert any("yasasvi" in s["scheme_id"] for s in search.json()["results"])
    sid = records()[0]["scheme_id"]
    detail = client.get("/api/scholarships/" + sid)
    assert detail.status_code == 200 and detail.json()["scholarship"]["eligibility"]
    assert client.get("/api/scholarships/unknown").status_code == 404


def test_session_token_required(client):
    result = client.post("/api/sessions", {}, format="json")
    assert result.status_code == 201
    session = result.json()
    path = "/api/sessions/" + session["session_id"]
    assert client.get(path).status_code == 404
    assert client.get(path, HTTP_X_SESSION_TOKEN=session["session_token"]).status_code == 200


def test_admin_endpoints_protected(client):
    assert client.post("/api/admin/ingest", {}, format="json").status_code in (401, 403)
    assert client.get("/api/agent/usage").status_code in (401, 403)


def test_request_id_and_invalid_input(client):
    response = client.post(
        "/api/agent/query",
        {"question": "Pragati", "profile": {"age": 20}},
        format="json",
        HTTP_X_REQUEST_ID="test-request",
    )
    assert response.status_code == 400
    assert response["X-Request-ID"] == "test-request"
    assert "unknown" not in str(response.json()["error"])


def test_invalid_session_and_delete(client):
    assert client.get("/api/sessions/not-a-uuid").status_code == 404
    session = client.post("/api/sessions", {}, format="json").json()
    path = "/api/sessions/" + session["session_id"]
    assert client.delete(path).status_code == 404
    assert client.delete(path, HTTP_X_SESSION_TOKEN=session["session_token"]).status_code == 204
    assert client.get(path, HTTP_X_SESSION_TOKEN=session["session_token"]).status_code == 404


def test_health_exposes_real_index_status(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["dataset"]["records"] == 16
    assert isinstance(response.json()["vector_index"]["ready"], bool)


def test_json_declares_utf8_for_windows_clients(client):
    response = client.get("/api/health")
    assert "charset=utf-8" in response["Content-Type"]
