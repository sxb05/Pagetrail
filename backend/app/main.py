import logging
import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes.auth import router as auth_router
from app.api.routes.chat import router as chat_router
from app.api.routes.health import router as health_router
from app.core.paths import BRAND_ICON, FRONTEND_DIST, FRONTEND_DIR, FRONTEND_PUBLIC
from app.db.session import init_db
from app.services.rag import init_rag_db

logger = logging.getLogger(__name__)

cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

app = FastAPI(title="PageTrail")
app.include_router(auth_router)
app.include_router(health_router)
app.include_router(chat_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_error_handler(_request: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.exception("Database error", exc_info=exc)
    return JSONResponse(
        status_code=503,
        content={"detail": "The database is temporarily unavailable. Please try again."},
    )


@app.on_event("startup")
def startup() -> None:
    # Create the RAG table before init_db enables RLS on it.
    init_rag_db()
    init_db()


@app.get("/")
async def root_to_login():
    return RedirectResponse(url="/login")


def _frontend_file(path: str) -> Path | None:
    root = FRONTEND_DIST.resolve()
    requested = (root / path).resolve()
    if requested != root and root not in requested.parents:
        return None
    return requested if requested.is_file() else None


@app.get("/pagetrail-icon.png", include_in_schema=False)
@app.get("/favicon.png", include_in_schema=False)
def brand_icon(request: Request) -> FileResponse:
    name = Path(request.url.path).name
    for candidate in (
        FRONTEND_DIST / name,
        FRONTEND_PUBLIC / name,
        FRONTEND_DIR / name,
        BRAND_ICON,
    ):
        if candidate.is_file():
            return FileResponse(candidate, media_type="image/png")
    raise HTTPException(status_code=404, detail="Icon not found.")


if FRONTEND_DIST.exists():
    assets = FRONTEND_DIST / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str) -> FileResponse:
        requested = _frontend_file(path)
        if requested is not None:
            return FileResponse(requested)
        return FileResponse(FRONTEND_DIST / "index.html")


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
