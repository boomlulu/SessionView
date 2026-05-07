from __future__ import annotations

import os
import platform
import sqlite3
import sys
import threading
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Optional

from .config import DEFAULT_DB_PATH, DEFAULT_SCAN_ROOTS, ensure_app_dir, normalize_roots
from .index import checkpoint, connect, index_session, init_db, rebuild_db
from .models import ParsedSession
from .parser import parse_transcript
from .scanner import infer_project_path, iter_transcripts
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
_MAX_PENDING_MULTIPLIER = 4


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
    conn = open_db(db_path)
    scan_roots = _resolve_scan_roots(conn, roots)
    if rebuild:
        rebuild_db(conn)
    report = {
        "roots": [str(root) for root in scan_roots],
        "scanned_files": 0,
        "indexed_sessions": 0,
        "warnings": [],
    }
    report.update(_scan_and_index(scan_roots, conn))
    _mark_scan_roots_scanned(conn, scan_roots)
    conn.commit()
    checkpoint(conn)
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
            return _scan_status_snapshot()
    conn = open_db(db_path)
    scan_roots = _resolve_scan_roots(conn, roots)
    root_payload = _scan_root_payload(conn)
    conn.close()
    with _SCAN_LOCK:
        if _SCAN_STATUS["running"]:
            return _scan_status_snapshot()
        _SCAN_STATUS.update(
            {
                "running": True,
                "phase": "starting",
                "roots": root_payload,
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
        return _scan_status_snapshot()


def _run_scan_job(scan_roots, rebuild: bool, db_path: Path) -> None:
    conn = None
    try:
        _update_scan_status(phase="discovering")
        conn = open_db(db_path)
        if rebuild:
            rebuild_db(conn)

        def on_discovered(transcript: Path) -> None:
            with _SCAN_LOCK:
                _SCAN_STATUS["total_files"] += 1
                _SCAN_STATUS["phase"] = "indexing"
                _SCAN_STATUS["current_file"] = str(transcript)

        def on_processed(indexed: bool, warnings: list[str]) -> None:
            with _SCAN_LOCK:
                _SCAN_STATUS["scanned_files"] += 1
                if indexed:
                    _SCAN_STATUS["indexed_sessions"] += 1
                _SCAN_STATUS["warnings"].extend(warnings)

        _scan_and_index(scan_roots, conn, on_discovered=on_discovered, on_processed=on_processed)
        final_stats = stats(conn)
        _mark_scan_roots_scanned(conn, scan_roots)
        conn.commit()
        checkpoint(conn)
        _update_scan_status(
            running=False,
            phase="done",
            roots=_scan_root_payload(conn),
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


def _scan_status_snapshot() -> Dict[str, Any]:
    payload = dict(_SCAN_STATUS)
    payload["roots"] = [dict(root) for root in _SCAN_STATUS["roots"]]
    payload["warnings"] = list(_SCAN_STATUS["warnings"])
    return payload


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _scan_and_index(
    scan_roots: list[Path],
    conn: sqlite3.Connection,
    on_discovered: Optional[Callable[[Path], None]] = None,
    on_processed: Optional[Callable[[bool, list[str]], None]] = None,
) -> Dict[str, Any]:
    report: Dict[str, Any] = {"scanned_files": 0, "indexed_sessions": 0, "warnings": []}
    max_workers = _scan_worker_count()
    max_pending = max(1, max_workers * _MAX_PENDING_MULTIPLIER)
    batch_size = _index_batch_size()
    pending = set()
    batch: list[ParsedSession] = []

    def flush_batch() -> None:
        nonlocal batch
        if not batch:
            return
        _index_sessions_batch(conn, batch)
        for session in batch:
            warnings = _format_session_warnings(session)
            report["scanned_files"] += 1
            report["indexed_sessions"] += 1
            report["warnings"].extend(warnings)
            if on_processed:
                on_processed(True, warnings)
        batch = []

    def handle_done(done) -> None:
        nonlocal batch
        for future in done:
            session, warning = future.result()
            if warning:
                report["scanned_files"] += 1
                report["warnings"].append(warning)
                if on_processed:
                    on_processed(False, [warning])
                continue
            batch.append(session)
            if len(batch) >= batch_size:
                flush_batch()

    with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="ccm-scan-parse") as executor:
        for transcript in iter_transcripts(scan_roots):
            if on_discovered:
                on_discovered(transcript)
            pending.add(executor.submit(_parse_transcript_task, transcript, scan_roots))
            if len(pending) >= max_pending:
                done, pending = wait(pending, return_when=FIRST_COMPLETED)
                handle_done(done)
        while pending:
            done, pending = wait(pending, return_when=FIRST_COMPLETED)
            handle_done(done)

    flush_batch()
    return report


def _parse_transcript_task(transcript: Path, scan_roots: list[Path]):
    try:
        return parse_transcript(transcript, project_path=infer_project_path(transcript, scan_roots)), None
    except Exception as exc:
        return None, f"{transcript}: {exc}"


def _index_sessions_batch(conn: sqlite3.Connection, sessions: list[ParsedSession]) -> None:
    with conn:
        for session in sessions:
            index_session(conn, session, commit=False)


def _format_session_warnings(session: ParsedSession) -> list[str]:
    return [f"{session.transcript_path}:{warning.line}: {warning.message}" for warning in session.warnings]


def _scan_worker_count() -> int:
    configured = os.environ.get("CCM_SCAN_WORKERS")
    if configured:
        try:
            return max(1, int(configured))
        except ValueError:
            pass
    cpu_count = os.cpu_count() or 4
    return min(16, max(4, cpu_count))


def _index_batch_size() -> int:
    configured = os.environ.get("CCM_INDEX_BATCH_SIZE")
    if configured:
        try:
            return max(1, int(configured))
        except ValueError:
            pass
    return 16


def scan_roots(db_path: str | Path = DEFAULT_DB_PATH):
    conn = open_db(db_path)
    payload = _scan_root_payload(conn)
    conn.close()
    _update_scan_status(roots=payload)
    return payload


def add_scan_root(path: str, db_path: str | Path = DEFAULT_DB_PATH):
    root = Path(path).expanduser().resolve()
    now = _now()
    conn = open_db(db_path)
    with conn:
        conn.execute(
            """
            INSERT INTO scan_roots (path, created_at, updated_at, active)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(path) DO UPDATE SET
                updated_at = excluded.updated_at,
                active = 1
            """,
            (str(root), now, now),
        )
    payload = _scan_root_payload(conn)
    conn.close()
    _update_scan_status(roots=payload)
    return payload


def remove_scan_root(path: str, db_path: str | Path = DEFAULT_DB_PATH):
    root = Path(path).expanduser().resolve()
    candidates = {path, str(root)}
    conn = open_db(db_path)
    with conn:
        for candidate in candidates:
            conn.execute("UPDATE scan_roots SET active = 0, updated_at = ? WHERE path = ?", (_now(), candidate))
    payload = _scan_root_payload(conn)
    conn.close()
    _update_scan_status(roots=payload)
    return payload


def refresh_scan_status_from_db(db_path: str | Path = DEFAULT_DB_PATH) -> Dict[str, Any]:
    conn = open_db(db_path)
    root_payload = _scan_root_payload(conn)
    db_stats = stats(conn)
    conn.close()
    _update_scan_status(roots=root_payload, session_count=db_stats["session_count"])
    return scan_status()


def _resolve_scan_roots(conn: sqlite3.Connection, roots: Optional[Iterable[str]]) -> list[Path]:
    if roots is not None:
        scan_roots = normalize_roots(roots)
        _upsert_scan_roots(conn, scan_roots)
        return scan_roots
    rows = conn.execute(
        "SELECT path FROM scan_roots WHERE active = 1 ORDER BY created_at ASC, path ASC"
    ).fetchall()
    return [Path(row["path"]).expanduser().resolve() for row in rows]


def _upsert_scan_roots(conn: sqlite3.Connection, roots: Iterable[Path]) -> None:
    now = _now()
    with conn:
        for root in roots:
            conn.execute(
                """
                INSERT INTO scan_roots (path, created_at, updated_at, active)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(path) DO UPDATE SET
                    updated_at = excluded.updated_at,
                    active = 1
                """,
                (str(root), now, now),
            )


def _mark_scan_roots_scanned(conn: sqlite3.Connection, roots: Iterable[Path]) -> None:
    now = _now()
    with conn:
        for root in roots:
            conn.execute(
                "UPDATE scan_roots SET last_scanned_at = ?, updated_at = ? WHERE path = ?",
                (now, now, str(root)),
            )


def _scan_root_payload(conn: sqlite3.Connection):
    rows = conn.execute(
        """
        SELECT path, created_at, updated_at, last_scanned_at
        FROM scan_roots
        WHERE active = 1
        ORDER BY created_at ASC, path ASC
        """
    ).fetchall()
    return [
        {
            "path": row["path"],
            "exists": Path(row["path"]).expanduser().exists(),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "last_scanned_at": row["last_scanned_at"],
        }
        for row in rows
    ]


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
    payload = _project_payload(conn)
    conn.close()
    return payload


def _project_payload(conn: sqlite3.Connection):
    projects = set(list_projects(conn))
    for root in _scan_root_payload(conn):
        projects.add(root["path"])
    return sorted(project for project in projects if project)


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
