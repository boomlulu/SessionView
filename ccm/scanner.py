from __future__ import annotations

from pathlib import Path
from typing import Iterable, Iterator, Optional

from .config import DEFAULT_SCAN_ROOTS
from .models import ParsedSession
from .parser import parse_transcript


def iter_transcripts(roots: Optional[Iterable[str | Path]] = None) -> Iterator[Path]:
    scan_roots = list(roots) if roots else DEFAULT_SCAN_ROOTS
    seen = set()
    for root_path in _expand_scan_roots(scan_roots):
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
    root_paths = list(roots)
    for root in root_paths:
        try:
            relative = transcript_path.relative_to(root)
        except ValueError:
            continue
        if len(relative.parts) >= 2:
            decoded = _decode_claude_project_dir(relative.parts[0])
            return decoded or str(root / relative.parts[0])
    if root_paths:
        return str(root_paths[0])
    parent = transcript_path.parent
    return str(parent) if parent else None


def _decode_claude_project_dir(name: str) -> Optional[str]:
    if not name.startswith("-"):
        return None
    parts = [part for part in name.split("-") if part]
    if not parts:
        return None
    return "/" + "/".join(parts)


def _expand_scan_roots(roots: Iterable[str | Path]) -> Iterator[Path]:
    yielded = set()
    for root in roots:
        root_path = Path(root).expanduser()
        candidates = [root_path]
        if _should_try_claude_project_mapping(root_path):
            candidates.extend(_claude_project_candidates(root_path))
        for candidate in candidates:
            if candidate in yielded:
                continue
            yielded.add(candidate)
            yield candidate


def _should_try_claude_project_mapping(path: Path) -> bool:
    if path.suffix == ".jsonl":
        return False
    if not path.exists() or not path.is_dir():
        return True
    try:
        next(path.rglob("*.jsonl"))
        return False
    except StopIteration:
        return True


def _claude_project_candidates(path: Path) -> list[Path]:
    candidates: list[Path] = []
    if path.suffix == ".jsonl":
        return candidates
    bases = [Path("~/.claude/projects").expanduser(), Path("~/.config/claude/projects").expanduser()]
    ancestors = [path, *path.parents]
    for ancestor in ancestors:
        encoded_names = {_encode_claude_project_dir(ancestor)}
        encoded_names.add(_encode_claude_project_dir(Path(str(ancestor).replace("_", "-"))))
        ancestor_matches = []
        for base in bases:
            for name in encoded_names:
                candidate = base / name
                if candidate.exists():
                    ancestor_matches.append(candidate)
        if ancestor_matches:
            candidates.extend(ancestor_matches)
            break
    return candidates


def _encode_claude_project_dir(path: Path) -> str:
    parts = [part for part in str(path.expanduser()).split("/") if part]
    return "-" + "-".join(parts)
