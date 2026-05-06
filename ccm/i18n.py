from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List


ROOT = Path(__file__).resolve().parent.parent
LOCALE_DIRS = [
    ROOT / "web" / "dist" / "locales",
    ROOT / "web" / "public" / "locales",
]


def locale_dir() -> Path:
    for path in LOCALE_DIRS:
        if path.exists():
            return path
    return LOCALE_DIRS[-1]


def list_languages() -> List[Dict[str, str]]:
    languages = []
    for path in sorted(locale_dir().glob("*.csv")):
        meta = _read_metadata(path)
        code = path.stem
        languages.append(
            {
                "code": code,
                "name": meta.get("__language_name", code),
                "native_name": meta.get("__language_native_name", meta.get("__language_name", code)),
            }
        )
    return languages


def _read_metadata(path: Path) -> Dict[str, str]:
    metadata: Dict[str, str] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            key = (row.get("key") or "").strip()
            value = (row.get("value") or "").strip()
            if key.startswith("__"):
                metadata[key] = value
    return metadata
