from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ParseWarning:
    line: int
    message: str


@dataclass
class ParsedMessage:
    ordinal: int
    role: str
    text: str
    timestamp: Optional[str] = None
    uuid: Optional[str] = None
    parent_uuid: Optional[str] = None
    raw_json: Optional[Dict[str, Any]] = None


@dataclass
class ParsedSession:
    id: str
    transcript_path: Path
    project_path: Optional[str] = None
    name: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    first_user_text: Optional[str] = None
    messages: List[ParsedMessage] = field(default_factory=list)
    warnings: List[ParseWarning] = field(default_factory=list)
    raw_metadata: Optional[Dict[str, Any]] = None

    @property
    def message_count(self) -> int:
        return len(self.messages)


@dataclass
class ScanReport:
    roots: List[str]
    scanned_files: int = 0
    indexed_sessions: int = 0
    warnings: List[str] = field(default_factory=list)


@dataclass
class SearchResult:
    session_id: str
    project_path: Optional[str]
    transcript_path: str
    created_at: Optional[str]
    updated_at: Optional[str]
    first_user_text: Optional[str]
    message_count: int
    snippet: Optional[str]
    resume_command: str
