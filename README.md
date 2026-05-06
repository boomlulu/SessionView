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

The MVP is local-only. It does not call remote LLMs, does not modify transcript files, and does not execute resume commands from the browser.
