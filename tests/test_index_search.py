import sqlite3
from pathlib import Path

from ccm.index import index_session, init_db
from ccm.parser import parse_transcript
from ccm.search import get_session, list_projects, search_sessions


FIXTURES = Path(__file__).parent / "fixtures"


def make_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    return conn


def test_index_is_idempotent_and_searches_fts():
    conn = make_conn()
    session = parse_transcript(FIXTURES / "sample_session.jsonl")

    index_session(conn, session)
    index_session(conn, session)

    message_count = conn.execute("SELECT COUNT(*) AS count FROM messages").fetchone()["count"]
    results = search_sessions(conn, "orchid")

    assert message_count == 2
    assert len(results) == 1
    assert results[0]["session_id"] == "sample-session"
    assert "claude --resume sample-session" == results[0]["resume_command"]


def test_project_filter_and_detail():
    conn = make_conn()
    index_session(conn, parse_transcript(FIXTURES / "sample_session.jsonl"))
    index_session(conn, parse_transcript(FIXTURES / "second_project" / "second_session.jsonl"))

    assert "/tmp/second-project" in list_projects(conn)
    results = search_sessions(conn, "atlas", project="/tmp/second-project")
    detail = get_session(conn, "second-session")

    assert [item["session_id"] for item in results] == ["second-session"]
    assert detail is not None
    assert detail["transcript_path"].endswith("second_session.jsonl")
    assert detail["message_count"] == 2
