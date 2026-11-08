from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from app.config import get_settings


def _is_inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def mount_frontend(application: FastAPI) -> None:
    @application.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        if full_path == "api" or full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        dist = get_settings().resolved_frontend_dist
        index = dist / "index.html"
        if not index.is_file():
            raise HTTPException(status_code=404, detail="Not Found")
        if full_path:
            candidate = dist / full_path
            if candidate.is_file() and _is_inside(candidate, dist):
                return FileResponse(candidate)
        return FileResponse(index)
