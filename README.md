# SessionView

Local Claude Code session manager for scanning transcript JSONL files, indexing them in SQLite FTS5, and finding old sessions from a small web UI.

## Install

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
cd web && npm install && npm run build && cd ..
```

## CLI

```bash
python -m ccm.cli doctor
python -m ccm.cli scan --root tests/fixtures --rebuild
python -m ccm.cli serve
```

By default, scans look in:

- `~/.claude/projects`
- `~/.config/claude/projects`

The index database defaults to `~/.cc-session-manager/index.sqlite`. Override it with `--db` or `CCM_DB`.

## Web UI

Open `http://127.0.0.1:8765`, click scan, search by keyword, filter by project, open a session detail, and copy the generated `claude --resume <session-id>` command.

The scan status panel shows the roots being scanned, whether each root exists, the current phase, current file, indexed count, and recent warnings. The UI uses `POST /api/scan/start` and polls `GET /api/scan/status`; the original synchronous `POST /api/scan` remains available for scripts and tests.

## Languages

The UI loads translations from CSV files in `web/public/locales/`. English and Chinese are included by default.

To add another language without changing code, add a CSV file such as `web/public/locales/ja.csv` with the same `key,value` columns. After building, the file is copied to `web/dist/locales/`; for an already built deployment, place the new CSV in `web/dist/locales/`.

The MVP is local-only. It does not call remote LLMs, does not modify transcript files, and does not execute resume commands from the browser.
