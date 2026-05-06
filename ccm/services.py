from __future__ import annotations

import platform
import sqlite3
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from .config import DEFAULT_DB_PATH, DEFAULT_SCAN_ROOTS, ensure_app_dir, normalize_roots
from .index import connect, index_session, init_db, rebuild_db
from .parser import parse_transcript
from .scanner import infer_project_path, iter_transcripts, scan_transcripts
from .search import get_session, list_projects, list_sessions, search_sessions, stats


_SCAN_LOCK = threading.Lock()
_SCAN_STATUS: Dict[str, Any] = {
    "running": False,
    "phase": "idle",
    "roots": [{"path": str(root), "exists": root.exists()} for root in DEFAULT_SCAN_ROOTS],
    "total_files": 0,
    "scanned_files": 0,
    "indexed_sessions": 0,
    "current_file": None,
    "warnings": [],
    "error": None,
    "started_at": None,
    "finished_at": None,
    "session_count": 0,
}


def open_db(db_path: str | Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    ensure_app_dir()
    conn = connect(db_path)
    init_db(conn)
    return conn


def run_scan(
    roots: Optional[Iterable[str]] = None,
    rebuild: bool = False,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> Dict[str, Any]:
    scan_roots = normalize_roots(roots)
    conn = open_db(db_path)
    if rebuild:
        rebuild_db(conn)
    report = {
        "roots": [str(root) for root in scan_roots],
        "scanned_files": 0,
        "indexed_sessions": 0,
        "warnings": [],
    }
    for session in scan_transcripts(scan_roots):
        report["scanned_files"] += 1
        index_session(conn, session)
        report["indexed_sessions"] += 1
        for warning in session.warnings:
            report["warnings"].append(f"{session.transcript_path}:{warning.line}: {warning.message}")
    report.update(stats(conn))
    conn.close()
    return report


def start_scan(
    roots: Optional[Iterable[str]] = None,
    rebuild: bool = False,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> Dict[str, Any]:
    with _SCAN_LOCK:
        if _SCAN_STATUS["running"]:
            return dict(_SCAN_STATUS)
        scan_roots = normalize_roots(roots)
        _SCAN_STATUS.update(
            {
                "running": True,
                "phase": "starting",
                "roots": [{"path": str(root), "exists": root.exists()} for root in scan_roots],
                "total_files": 0,
                "scanned_files": 0,
                "indexed_sessions": 0,
                "current_file": None,
                "warnings": [],
                "error": None,
                "started_at": _now(),
                "finished_at": None,
            }
        )
    thread = threading.Thread(target=_run_scan_job, args=(scan_roots, rebuild, Path(db_path)), daemon=True)
    thread.start()
    return scan_status()


def scan_status(db_path: str | Path = DEFAULT_DB_PATH) -> Dict[str, Any]:
    with _SCAN_LOCK:
        payload = dict(_SCAN_STATUS)
    if not payload["running"]:
        try:
            conn = open_db(db_path)
            payload.update(stats(conn))
            conn.close()
        except sqlite3.DatabaseError:
            pass
    return payload


def _run_scan_job(scan_roots, rebuild: bool, db_path: Path) -> None:
    conn = None
    try:
        _update_scan_status(phase="discovering")
        transcripts = list(iter_transcripts(scan_roots))
        _update_scan_status(total_files=len(transcripts), phase="indexing")
        conn = open_db(db_path)
        if rebuild:
            rebuild_db(conn)
        for transcript in transcripts:
            _update_scan_status(current_file=str(transcript))
            session = parse_transcript(transcript, project_path=infer_project_path(transcript, scan_roots))
            index_session(conn, session)
            warnings = [f"{session.transcript_path}:{warning.line}: {warning.message}" for warning in session.warnings]
            with _SCAN_LOCK:
                _SCAN_STATUS["scanned_files"] += 1
                _SCAN_STATUS["indexed_sessions"] += 1
                _SCAN_STATUS["warnings"].extend(warnings)
        final_stats = stats(conn)
        _update_scan_status(
            running=False,
            phase="done",
            current_file=None,
            finished_at=_now(),
            session_count=final_stats["session_count"],
        )
    except Exception as exc:  # pragma: no cover - defensive status for unexpected scanner failures.
        _update_scan_status(running=False, phase="failed", error=str(exc), finished_at=_now())
    finally:
        if conn is not None:
            conn.close()


def _update_scan_status(**values: Any) -> None:
    with _SCAN_LOCK:
        _SCAN_STATUS.update(values)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def health(db_path: str | Path = DEFAULT_DB_PATH) -> Dict[str, Any]:
    conn = open_db(db_path)
    payload = {"ok": True, "db_path": str(Path(db_path).expanduser()), **stats(conn)}
    conn.close()
    return payload


def sessions(project: Optional[str] = None, limit: int = 100, db_path: str | Path = DEFAULT_DB_PATH):
    conn = open_db(db_path)
    payload = list_sessions(conn, project=project, limit=limit)
    conn.close()
    return payload


def session_detail(session_id: str, db_path: str | Path = DEFAULT_DB_PATH):
    conn = open_db(db_path)
    payload = get_session(conn, session_id)
    conn.close()
    return payload


def search(query: str, project: Optional[str] = None, limit: int = 20, db_path: str | Path = DEFAULT_DB_PATH):
    conn = open_db(db_path)
    payload = search_sessions(conn, query=query, project=project, limit=limit)
    conn.close()
    return payload


def projects(db_path: str | Path = DEFAULT_DB_PATH):
    conn = open_db(db_path)
    payload = list_projects(conn)
    conn.close()
    return payload


def doctor(db_path: str | Path = DEFAULT_DB_PATH) -> Dict[str, Any]:
    conn = open_db(db_path)
    try:
        conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS fts5_probe USING fts5(text)")
        fts5_ok = True
    except sqlite3.DatabaseError:
        fts5_ok = False
    finally:
        conn.execute("DROP TABLE IF EXISTS fts5_probe")
        conn.close()
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "sqlite": sqlite3.sqlite_version,
        "fts5": fts5_ok,
        "default_roots": [{"path": str(root), "exists": root.exists()} for root in DEFAULT_SCAN_ROOTS],
        "db_path": str(Path(db_path).expanduser()),
    }
