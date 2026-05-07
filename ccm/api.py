from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import i18n
from . import services


class ScanRequest(BaseModel):
    roots: Optional[List[str]] = None
    rebuild: bool = False


class ScanRootRequest(BaseModel):
    path: str


def create_app(db_path: Optional[str] = None) -> FastAPI:
    app = FastAPI(title="Claude Code Session Manager")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    effective_db = db_path or services.DEFAULT_DB_PATH
    services.refresh_scan_status_from_db(effective_db)

    @app.get("/api/health")
    def api_health():
        return services.health(effective_db)

    @app.post("/api/scan")
    def api_scan(request: ScanRequest):
        return services.run_scan(request.roots, request.rebuild, effective_db)

    @app.post("/api/scan/start")
    def api_scan_start(request: ScanRequest):
        return services.start_scan(request.roots, request.rebuild, effective_db)

    @app.get("/api/scan/status")
    async def api_scan_status():
        return services.scan_status(effective_db)

    @app.get("/api/scan/roots")
    def api_scan_roots():
        return services.scan_roots(effective_db)

    @app.post("/api/scan/roots")
    def api_add_scan_root(request: ScanRootRequest):
        return services.add_scan_root(request.path, effective_db)

    @app.delete("/api/scan/roots")
    def api_remove_scan_root(request: ScanRootRequest):
        return services.remove_scan_root(request.path, effective_db)

    @app.get("/api/sessions")
    def api_sessions(project: Optional[str] = None, limit: int = 100):
        return services.sessions(project=project, limit=limit, db_path=effective_db)

    @app.get("/api/sessions/{session_id}")
    def api_session_detail(session_id: str):
        payload = services.session_detail(session_id, effective_db)
        if payload is None:
            raise HTTPException(status_code=404, detail="session not found")
        return payload

    @app.get("/api/search")
    def api_search(q: str = "", project: Optional[str] = None, limit: int = 20):
        return services.search(q, project=project, limit=limit, db_path=effective_db)

    @app.get("/api/projects")
    def api_projects():
        return services.projects(effective_db)

    @app.get("/api/i18n/languages")
    def api_languages():
        return i18n.list_languages()

    web_dist = Path(__file__).resolve().parent.parent / "web" / "dist"
    locale_dir = i18n.locale_dir()
    if locale_dir.exists():
        app.mount("/locales", StaticFiles(directory=str(locale_dir)), name="locales")
    if web_dist.exists():
        app.mount("/assets", StaticFiles(directory=str(web_dist / "assets")), name="assets")

        @app.get("/")
        def web_index():
            return FileResponse(str(web_dist / "index.html"))

    return app


app = create_app()
