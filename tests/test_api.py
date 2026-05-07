from pathlib import Path
import time

from fastapi.testclient import TestClient

from ccm import services
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


def test_api_lists_csv_languages(tmp_path):
    client = TestClient(create_app(str(tmp_path / "index.sqlite")))

    response = client.get("/api/i18n/languages")

    assert response.status_code == 200
    codes = {item["code"] for item in response.json()}
    assert {"en", "zh"}.issubset(codes)


def test_api_async_scan_status(tmp_path):
    client = TestClient(create_app(str(tmp_path / "index.sqlite")))

    started = client.post("/api/scan/start", json={"roots": [str(FIXTURES)], "rebuild": True})
    assert started.status_code == 200
    assert started.json()["roots"][0]["exists"] is True

    status = started.json()
    for _ in range(20):
        status = client.get("/api/scan/status").json()
        if not status["running"]:
            break
        time.sleep(0.05)

    assert status["phase"] == "done"
    assert status["total_files"] == 3
    assert status["scanned_files"] == 3
    assert status["indexed_sessions"] == 3
    assert status["session_count"] == 3


def test_async_scanned_sessions_persist_after_restart(tmp_path):
    db_path = tmp_path / "index.sqlite"
    client = TestClient(create_app(str(db_path)))
    started = client.post("/api/scan/start", json={"roots": [str(FIXTURES)], "rebuild": True})
    assert started.status_code == 200

    for _ in range(20):
        status = client.get("/api/scan/status").json()
        if not status["running"]:
            break
        time.sleep(0.05)
    assert status["phase"] == "done"
    assert status["session_count"] == 3

    restarted_client = TestClient(create_app(str(db_path)))
    health = restarted_client.get("/api/health")
    search = restarted_client.get("/api/search", params={"q": "orchid"})
    detail = restarted_client.get("/api/sessions/sample-session")

    assert health.status_code == 200
    assert health.json()["session_count"] == 3
    assert {item["session_id"] for item in search.json()} == {"sample-session", "bad-session"}
    assert detail.status_code == 200
    assert detail.json()["resume_command"] == "claude --resume sample-session"


def test_scan_status_does_not_touch_database(tmp_path, monkeypatch):
    client = TestClient(create_app(str(tmp_path / "index.sqlite")))

    def fail_open_db(*args, **kwargs):
        raise AssertionError("status endpoint should not open sqlite")

    monkeypatch.setattr(services, "open_db", fail_open_db)
    response = client.get("/api/scan/status")

    assert response.status_code == 200
    assert "running" in response.json()


def test_scan_roots_are_persisted_and_removable(tmp_path):
    db_path = tmp_path / "index.sqlite"
    client = TestClient(create_app(str(db_path)))

    created = client.post("/api/scan/roots", json={"path": str(FIXTURES)})
    assert created.status_code == 200
    assert str(FIXTURES.resolve()) in {item["path"] for item in created.json()}

    restarted_client = TestClient(create_app(str(db_path)))
    persisted = restarted_client.get("/api/scan/roots")
    assert persisted.status_code == 200
    assert str(FIXTURES.resolve()) in {item["path"] for item in persisted.json()}

    removed = restarted_client.request("DELETE", "/api/scan/roots", json={"path": str(FIXTURES)})
    assert removed.status_code == 200
    assert str(FIXTURES.resolve()) not in {item["path"] for item in removed.json()}

    still_removed = TestClient(create_app(str(db_path))).get("/api/scan/roots")
    assert str(FIXTURES.resolve()) not in {item["path"] for item in still_removed.json()}


def test_projects_include_scan_roots_before_sessions(tmp_path):
    db_path = tmp_path / "index.sqlite"
    client = TestClient(create_app(str(db_path)))
    root = str(FIXTURES.resolve())

    client.post("/api/scan/roots", json={"path": root})
    response = client.get("/api/projects")

    assert response.status_code == 200
    assert root in response.json()
