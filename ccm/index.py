from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable, Iterator

from .models import ParsedMessage, ParsedSession


def connect(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            name TEXT NULL,
            project_path TEXT NULL,
            transcript_path TEXT NOT NULL,
            created_at TEXT NULL,
            updated_at TEXT NULL,
            first_user_text TEXT NULL,
            message_count INTEGER NOT NULL DEFAULT 0,
            scan_status TEXT NOT NULL,
            scan_error TEXT NULL,
            raw_metadata TEXT NULL
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
            ordinal INTEGER NOT NULL,
            role TEXT NOT NULL,
            timestamp TEXT NULL,
            uuid TEXT NULL,
            parent_uuid TEXT NULL,
            text TEXT NOT NULL,
            raw_json TEXT NULL,
            UNIQUE(session_id, ordinal)
        );

        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
            message_id INTEGER NULL REFERENCES messages(id) ON DELETE CASCADE,
            chunk_index INTEGER NOT NULL,
            text TEXT NOT NULL
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
            text,
            session_id UNINDEXED,
            message_id UNINDEXED,
            chunk_id UNINDEXED
        );

        CREATE INDEX IF NOT EXISTS idx_sessions_project ON sessions(project_path);
        CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
        CREATE INDEX IF NOT EXISTS idx_chunks_session ON chunks(session_id);
        """
    )
    conn.commit()


def rebuild_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DROP TABLE IF EXISTS chunks_fts;
        DROP TABLE IF EXISTS chunks;
        DROP TABLE IF EXISTS messages;
        DROP TABLE IF EXISTS sessions;
        """
    )
    init_db(conn)


def index_session(conn: sqlite3.Connection, session: ParsedSession) -> None:
    with conn:
        conn.execute("DELETE FROM chunks_fts WHERE session_id = ?", (session.id,))
        conn.execute("DELETE FROM messages WHERE session_id = ?", (session.id,))
        conn.execute("DELETE FROM chunks WHERE session_id = ?", (session.id,))
        conn.execute(
            """
            INSERT INTO sessions (
                id, name, project_path, transcript_path, created_at, updated_at,
                first_user_text, message_count, scan_status, scan_error, raw_metadata
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ok', NULL, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                project_path = excluded.project_path,
                transcript_path = excluded.transcript_path,
                created_at = excluded.created_at,
                updated_at = excluded.updated_at,
                first_user_text = excluded.first_user_text,
                message_count = excluded.message_count,
                scan_status = excluded.scan_status,
                scan_error = excluded.scan_error,
                raw_metadata = excluded.raw_metadata
            """,
            (
                session.id,
                session.name,
                session.project_path,
                str(session.transcript_path),
                session.created_at,
                session.updated_at,
                session.first_user_text,
                session.message_count,
                json.dumps(session.raw_metadata) if session.raw_metadata else None,
            ),
        )
        for message in session.messages:
            message_id = _insert_message(conn, session.id, message)
            for chunk_index, text in enumerate(chunk_text(message.text)):
                cursor = conn.execute(
                    "INSERT INTO chunks (session_id, message_id, chunk_index, text) VALUES (?, ?, ?, ?)",
                    (session.id, message_id, chunk_index, text),
                )
                chunk_id = int(cursor.lastrowid)
                conn.execute(
                    "INSERT INTO chunks_fts (rowid, text, session_id, message_id, chunk_id) VALUES (?, ?, ?, ?, ?)",
                    (chunk_id, text, session.id, message_id, chunk_id),
                )


def _insert_message(conn: sqlite3.Connection, session_id: str, message: ParsedMessage) -> int:
    cursor = conn.execute(
        """
        INSERT INTO messages (
            session_id, ordinal, role, timestamp, uuid, parent_uuid, text, raw_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            message.ordinal,
            message.role,
            message.timestamp,
            message.uuid,
            message.parent_uuid,
            message.text,
            json.dumps(message.raw_json) if message.raw_json else None,
        ),
    )
    return int(cursor.lastrowid)


def chunk_text(text: str, size: int = 1200, overlap: int = 120) -> Iterator[str]:
    clean = " ".join(text.split())
    if not clean:
        return
    start = 0
    while start < len(clean):
        yield clean[start : start + size]
        if start + size >= len(clean):
            break
        start += max(1, size - overlap)
