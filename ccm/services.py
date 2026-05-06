from __future__ import annotations

import platform
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from .config import DEFAULT_DB_PATH, DEFAULT_SCAN_ROOTS, ensure_app_dir, normalize_roots
from .index import connect, index_session, init_db, rebuild_db
from .scanner import scan_transcripts
from .search import get_session, list_projects, list_sessions, search_sessions, stats


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
