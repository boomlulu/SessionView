from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import services


class ScanRequest(BaseModel):
    roots: Optional[List[str]] = None
    rebuild: bool = False


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

    @app.get("/api/health")
    def api_health():
        return services.health(effective_db)

    @app.post("/api/scan")
    def api_scan(request: ScanRequest):
        return services.run_scan(request.roots, request.rebuild, effective_db)

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

    web_dist = Path(__file__).resolve().parent.parent / "web" / "dist"
    if web_dist.exists():
        app.mount("/assets", StaticFiles(directory=str(web_dist / "assets")), name="assets")

        @app.get("/")
        def web_index():
            return FileResponse(str(web_dist / "index.html"))

    return app


app = create_app()
