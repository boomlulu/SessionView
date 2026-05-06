from pathlib import Path

from ccm.parser import parse_transcript


FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_normal_session():
    session = parse_transcript(FIXTURES / "sample_session.jsonl")

    assert session.id == "sample-session"
    assert session.project_path == "/tmp/sample-project"
    assert session.first_user_text.startswith("Please plan")
    assert session.message_count == 2
    assert session.messages[1].role == "assistant"
    assert "orchid" in session.messages[1].text


def test_parse_malformed_session_skips_bad_line():
    session = parse_transcript(FIXTURES / "malformed_session.jsonl")

    assert session.id == "bad-session"
    assert session.message_count == 2
    assert len(session.warnings) == 1
    assert "invalid json" in session.warnings[0].message
