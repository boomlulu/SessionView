from pathlib import Path

from ccm.scanner import infer_project_path, iter_transcripts


def test_project_directory_maps_to_claude_transcript_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    project_root = tmp_path / "work" / "HWMain_2022_Ranch"
    project_dir = project_root / "Assets" / "LocalResources" / "Ranch"
    project_dir.mkdir(parents=True)
    encoded = "-" + "-".join(part for part in str(project_root).replace("_", "-").split("/") if part)
    transcript_dir = tmp_path / ".claude" / "projects" / encoded
    transcript_dir.mkdir(parents=True)
    transcript = transcript_dir / "session.jsonl"
    transcript.write_text("{}", encoding="utf-8")

    found = list(iter_transcripts([project_dir]))

    assert found == [transcript.resolve()]
    assert infer_project_path(transcript, [project_dir.resolve()]) == str(project_dir.resolve())
