from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .models import ParsedMessage, ParsedSession, ParseWarning


def parse_transcript(path: str | Path, project_path: Optional[str] = None) -> ParsedSession:
    transcript_path = Path(path).expanduser()
    warnings: List[ParseWarning] = []
    messages: List[ParsedMessage] = []
    session_id: Optional[str] = None
    discovered_project = project_path

    with transcript_path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_number, line in enumerate(handle, start=1):
            raw_line = line.strip()
            if not raw_line:
                continue
            try:
                item = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                warnings.append(ParseWarning(line_number, f"invalid json: {exc.msg}"))
                continue

            if not isinstance(item, dict):
                warnings.append(ParseWarning(line_number, "json line is not an object"))
                continue

            session_id = session_id or _first_text(
                item,
                "sessionId",
                "session_id",
                "sessionID",
                "conversationId",
                "conversation_id",
            )
            discovered_project = discovered_project or _first_text(item, "cwd", "projectPath", "project_path")

            message = _parse_message(item, len(messages), line_number, warnings)
            if message:
                messages.append(message)

    resolved_id = session_id or transcript_path.stem
    first_user_text = next((msg.text for msg in messages if msg.role == "user" and msg.text), None)
    timestamps = [msg.timestamp for msg in messages if msg.timestamp]
    return ParsedSession(
        id=resolved_id,
        transcript_path=transcript_path,
        project_path=discovered_project,
        created_at=timestamps[0] if timestamps else None,
        updated_at=timestamps[-1] if timestamps else None,
        first_user_text=first_user_text,
        messages=messages,
        warnings=warnings,
    )


def _parse_message(
    item: Dict[str, Any],
    ordinal: int,
    line_number: int,
    warnings: List[ParseWarning],
) -> Optional[ParsedMessage]:
    message_obj = item.get("message")
    if message_obj is not None and not isinstance(message_obj, dict):
        warnings.append(ParseWarning(line_number, "message field is not an object"))
        message_obj = {}
    message_obj = message_obj or {}

    role = _first_text(message_obj, "role") or _first_text(item, "role", "type") or "unknown"
    if role == "human":
        role = "user"
    elif role == "ai":
        role = "assistant"

    content = message_obj.get("content", item.get("content"))
    text = extract_text(content)
    if not text:
        return None

    return ParsedMessage(
        ordinal=ordinal,
        role=role,
        text=text,
        timestamp=_first_text(item, "timestamp", "createdAt", "created_at"),
        uuid=_first_text(item, "uuid", "id") or _first_text(message_obj, "id"),
        parent_uuid=_first_text(item, "parentUuid", "parent_uuid", "parentId", "parent_id"),
        raw_json=item,
    )


def extract_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: List[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
                continue
            if not isinstance(block, dict):
                continue
            block_type = block.get("type")
            if block_type == "text" and isinstance(block.get("text"), str):
                parts.append(block["text"])
            elif block_type == "tool_result":
                parts.append(extract_text(block.get("content")))
        return "\n".join(part.strip() for part in parts if part and part.strip()).strip()
    if isinstance(content, dict):
        if isinstance(content.get("text"), str):
            return content["text"].strip()
        if "content" in content:
            return extract_text(content.get("content"))
    return ""


def _first_text(mapping: Dict[str, Any], *keys: str) -> Optional[str]:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str) and value:
            return value
    return None
