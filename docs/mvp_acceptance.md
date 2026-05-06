# MVP Acceptance

1. Create a Python environment and install the package with dev dependencies.
2. Run `python -m ccm.cli doctor` and confirm `fts5` is `true`.
3. Run `python -m ccm.cli scan --root tests/fixtures --rebuild`.
4. Run `python -m ccm.cli serve` and open `http://127.0.0.1:8765`.
5. Search for `orchid`; results should include matching snippets and detail preview.
6. Open a result and copy `claude --resume <session-id>`.
7. Repeat scan on the same fixture root; message counts must not duplicate.
8. Scan real Claude Code history from `~/.claude/projects` and search a remembered keyword.
