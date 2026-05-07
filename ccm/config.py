from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, List


APP_DIR = Path(os.environ.get("CCM_HOME", "~/.cc-session-manager")).expanduser()
DEFAULT_DB_PATH = Path(os.environ.get("CCM_DB", APP_DIR / "index.sqlite")).expanduser()
RANCH_DEFAULT_ROOT = Path("/Users/boom/work/HWMain_2022_Ranch/Assets/LocalResources/Ranch")

DEFAULT_SCAN_ROOTS = [RANCH_DEFAULT_ROOT] if RANCH_DEFAULT_ROOT.exists() else [
    Path("~/.claude/projects").expanduser(),
    Path("~/.config/claude/projects").expanduser(),
]


def ensure_app_dir() -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)


def normalize_roots(roots: Iterable[str] | None) -> List[Path]:
    if roots:
        return [Path(root).expanduser().resolve() for root in roots]
    return [root for root in DEFAULT_SCAN_ROOTS]


def display_path(path: str | Path | None) -> str | None:
    if path is None:
        return None
    try:
        return str(Path(path).expanduser().resolve())
    except OSError:
        return str(path)
