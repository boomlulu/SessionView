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

For local iteration, restart the server and rebuild the web UI with:

```bash
./scripts/restart_server.sh
```

Use `PORT=8766`, `CCM_DB=/path/to/index.sqlite`, or `BUILD_WEB=0` to override defaults.

By default, scans look in:

- `/Users/boom/work/HWMain_2022_Ranch/Assets/LocalResources/Ranch` on this machine while the Ranch workflow is being tuned.
- Otherwise `~/.claude/projects` and `~/.config/claude/projects`.

When a configured root is a project/resource directory rather than a Claude transcript directory, SessionView tries to map the nearest project ancestor to Claude's `~/.claude/projects/<encoded-path>` transcript folder.

The index database defaults to `~/.cc-session-manager/index.sqlite`. Override it with `--db` or `CCM_DB`.

## Web UI

Open `http://127.0.0.1:8765`, click scan, search by keyword, filter by project, open a session detail, and copy the generated `claude --resume <session-id>` command.

The scan status panel shows the roots being scanned, whether each root exists, the current phase, current file, indexed count, and recent warnings. Scan roots are stored in SQLite, so added paths persist after restarting the server. You can add or remove paths from the panel; the scan button uses the persisted active roots by default.

The UI uses `POST /api/scan/start` and polls `GET /api/scan/status`; status reads are served from in-memory scan state so they do not wait on SQLite while a scan is writing. The original synchronous `POST /api/scan` remains available for scripts and tests. Scan root management is exposed through `GET /api/scan/roots`, `POST /api/scan/roots`, and `DELETE /api/scan/roots`.

Scanning uses a threaded pipeline: transcript files are discovered incrementally, JSONL parsing runs in worker threads, and SQLite indexing is written by one writer in batches. Tune with `CCM_SCAN_WORKERS` and `CCM_INDEX_BATCH_SIZE` if your machine benefits from more or fewer workers.

The current SQLite database path is shown in the scan status panel. If sessions appear to disappear after restart, confirm the scan and serve commands are using the same `--db` value or the same `CCM_DB` environment variable.

## Languages

The UI loads translations from CSV files in `web/public/locales/`. English and Chinese are included by default.

To add another language without changing code, add a CSV file such as `web/public/locales/ja.csv` with the same `key,value` columns. After building, the file is copied to `web/dist/locales/`; for an already built deployment, place the new CSV in `web/dist/locales/`.

The MVP is local-only. It does not call remote LLMs, does not modify transcript files, and does not execute resume commands from the browser.
