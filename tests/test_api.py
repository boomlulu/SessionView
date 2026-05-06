from pathlib import Path

from fastapi.testclient import TestClient

from ccm.api import create_app


FIXTURES = Path(__file__).parent / "fixtures"


def test_api_scan_search_and_detail(tmp_path):
    db_path = tmp_path / "index.sqlite"
    client = TestClient(create_app(str(db_path)))

    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["session_count"] == 0

    scan = client.post("/api/scan", json={"roots": [str(FIXTURES)], "rebuild": True})
    assert scan.status_code == 200
    assert scan.json()["indexed_sessions"] == 3

    search = client.get("/api/search", params={"q": "orchid"})
    assert search.status_code == 200
    results = search.json()
    assert {item["session_id"] for item in results} == {"sample-session", "bad-session"}

    detail = client.get("/api/sessions/sample-session")
    assert detail.status_code == 200
    assert detail.json()["resume_command"] == "claude --resume sample-session"
