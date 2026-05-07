from __future__ import annotations

import re
import sqlite3
from typing import Any, Dict, List, Optional


def resume_command(session_id: str) -> str:
    return f"claude --resume {session_id}"


def list_sessions(conn: sqlite3.Connection, project: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    params: List[Any] = []
    where = ""
    if project:
        where = "WHERE project_path = ?"
        params.append(project)
    params.append(max(limit * 5, limit))
    rows = conn.execute(
        f"""
        SELECT id, name, project_path, transcript_path, created_at, updated_at,
               first_user_text, message_count
        FROM sessions
        {where}
        ORDER BY COALESCE(updated_at, created_at, id) DESC
        LIMIT ?
        """,
        params,
    ).fetchall()
    return [_session_row(row, snippet=None) for row in rows]


def get_session(conn: sqlite3.Connection, session_id: str) -> Optional[Dict[str, Any]]:
    row = conn.execute(
        """
        SELECT id, name, project_path, transcript_path, created_at, updated_at,
               first_user_text, message_count
        FROM sessions
        WHERE id = ?
        """,
        (session_id,),
    ).fetchone()
    if not row:
        return None
    messages = conn.execute(
        """
        SELECT id, ordinal, role, timestamp, uuid, parent_uuid, text
        FROM messages
        WHERE session_id = ?
        ORDER BY ordinal ASC
        LIMIT 80
        """,
        (session_id,),
    ).fetchall()
    chunks = conn.execute(
        """
        SELECT id, chunk_index, text
        FROM chunks
        WHERE session_id = ?
        ORDER BY id ASC
        LIMIT 20
        """,
        (session_id,),
    ).fetchall()
    payload = _session_row(row, snippet=None)
    payload["messages"] = [dict(message) for message in messages]
    payload["chunks"] = [dict(chunk) for chunk in chunks]
    return payload


def search_sessions(
    conn: sqlite3.Connection,
    query: str,
    project: Optional[str] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    query = (query or "").strip()
    if not query:
        return list_sessions(conn, project=project, limit=limit)

    fts_query = _to_fts_query(query)
    params: List[Any] = [fts_query]
    project_filter = ""
    if project:
        project_filter = "AND s.project_path = ?"
        params.append(project)
    params.append(limit)

    sql = f"""
        SELECT s.id, s.name, s.project_path, s.transcript_path, s.created_at,
               s.updated_at, s.first_user_text, s.message_count,
               snippet(chunks_fts, 0, '<mark>', '</mark>', '...', 18) AS snippet
        FROM chunks_fts
        JOIN sessions s ON s.id = chunks_fts.session_id
        WHERE chunks_fts MATCH ?
        {project_filter}
        ORDER BY COALESCE(s.updated_at, s.created_at, s.id) DESC
        LIMIT ?
    """
    try:
        rows = conn.execute(sql, params).fetchall()
    except sqlite3.OperationalError:
        rows = conn.execute(sql, [_quote_fts(query)] + params[1:]).fetchall()
    seen = set()
    results: List[Dict[str, Any]] = []
    for row in rows:
        if row["id"] in seen:
            continue
        seen.add(row["id"])
        results.append(_session_row(row, snippet=row["snippet"]))
        if len(results) >= limit:
            break
    return results


def list_projects(conn: sqlite3.Connection) -> List[str]:
    rows = conn.execute(
        """
        SELECT DISTINCT project_path
        FROM sessions
        WHERE project_path IS NOT NULL AND project_path != ''
        ORDER BY project_path ASC
        """
    ).fetchall()
    return [row["project_path"] for row in rows]


def stats(conn: sqlite3.Connection) -> Dict[str, Any]:
    row = conn.execute("SELECT COUNT(*) AS count FROM sessions").fetchone()
    return {"session_count": int(row["count"] if row else 0)}


def _session_row(row: sqlite3.Row, snippet: Optional[str]) -> Dict[str, Any]:
    return {
        "session_id": row["id"],
        "name": row["name"],
        "project_path": row["project_path"],
        "transcript_path": row["transcript_path"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "first_user_text": row["first_user_text"],
        "message_count": row["message_count"],
        "snippet": snippet,
        "resume_command": resume_command(row["id"]),
    }


def _to_fts_query(query: str) -> str:
    tokens = re.findall(r"[\w./:-]+", query, flags=re.UNICODE)
    if not tokens:
        return _quote_fts(query)
    return " AND ".join(_quote_fts(token) for token in tokens)


def _quote_fts(value: str) -> str:
    escaped = value.replace('"', '""')
    return f'"{escaped}"'
