from __future__ import annotations

from pathlib import Path
from typing import Iterable, Iterator, Optional

from .config import DEFAULT_SCAN_ROOTS
from .models import ParsedSession
from .parser import parse_transcript


def iter_transcripts(roots: Optional[Iterable[str | Path]] = None) -> Iterator[Path]:
    scan_roots = list(roots) if roots else DEFAULT_SCAN_ROOTS
    seen = set()
    for root in scan_roots:
        root_path = Path(root).expanduser()
        if not root_path.exists():
            continue
        if root_path.is_file() and root_path.suffix == ".jsonl":
            resolved = root_path.resolve()
            if resolved not in seen:
                seen.add(resolved)
                yield resolved
            continue
        for path in root_path.rglob("*.jsonl"):
            if path.is_file():
                resolved = path.resolve()
                if resolved not in seen:
                    seen.add(resolved)
                    yield resolved


def scan_transcripts(roots: Optional[Iterable[str | Path]] = None) -> Iterator[ParsedSession]:
    scan_roots = [Path(root).expanduser().resolve() for root in roots] if roots else DEFAULT_SCAN_ROOTS
    for transcript in iter_transcripts(scan_roots):
        yield parse_transcript(transcript, project_path=infer_project_path(transcript, scan_roots))


def infer_project_path(transcript_path: Path, roots: Iterable[Path]) -> Optional[str]:
    for root in roots:
        try:
            relative = transcript_path.relative_to(root)
        except ValueError:
            continue
        if len(relative.parts) >= 2:
            decoded = _decode_claude_project_dir(relative.parts[0])
            return decoded or str(root / relative.parts[0])
    parent = transcript_path.parent
    return str(parent) if parent else None


def _decode_claude_project_dir(name: str) -> Optional[str]:
    if not name.startswith("-"):
        return None
    parts = [part for part in name.split("-") if part]
    if not parts:
        return None
    return "/" + "/".join(parts)
