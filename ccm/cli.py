from __future__ import annotations

import argparse
import json
from typing import List, Optional

from . import services


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="ccm", description="Local Claude Code session manager")
    parser.add_argument("--db", default=str(services.DEFAULT_DB_PATH), help="SQLite index path")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("doctor", help="check local environment")

    scan_parser = subparsers.add_parser("scan", help="scan Claude Code transcript roots")
    scan_parser.add_argument("--root", action="append", default=None, help="root directory or JSONL file to scan")
    scan_parser.add_argument("--rebuild", action="store_true", help="rebuild the SQLite index first")

    serve_parser = subparsers.add_parser("serve", help="start the local API and web UI")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", default=8765, type=int)
    serve_parser.add_argument("--reload", action="store_true")

    args = parser.parse_args(argv)
    if args.command == "doctor":
        print(json.dumps(services.doctor(args.db), indent=2))
        return 0
    if args.command == "scan":
        print(json.dumps(services.run_scan(args.root, args.rebuild, args.db), indent=2))
        return 0
    if args.command == "serve":
        import uvicorn
        from .api import create_app

        print(f"Serving Claude Code Session Manager at http://{args.host}:{args.port}")
        uvicorn.run(create_app(args.db), host=args.host, port=args.port, reload=args.reload)
        return 0
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
