import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError

# Load environment variables before importing application modules.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

from app.api.routes.auth import router as auth_router  # noqa: E402
from app.api.routes.chat import router as chat_router  # noqa: E402
from app.api.routes.health import router as health_router  # noqa: E402
from app.core.paths import (  # noqa: E402
    BRAND_ICON,
    FRONTEND_DIST,
    FRONTEND_DIR,
    FRONTEND_PUBLIC,
)

logger = logging.getLogger(__name__)

cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Keep process startup independent from remote database availability."""
    logger.info("PageTrail application starting")
    yield
    logger.info("PageTrail application stopping")


app = FastAPI(title="PageTrail", lifespan=lifespan)

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
async def sqlalchemy_error_handler(
    _request: Request,
    exc: SQLAlchemyError,
) -> JSONResponse:
    logger.exception("Database error", exc_info=exc)
    return JSONResponse(
        status_code=503,
        content={
            "detail": ("The database is temporarily unavailable. " "Please try again.")
        },
    )


def _frontend_index() -> Path:
    """Return the built React entry point or fail clearly if missing."""
    dist_root = FRONTEND_DIST.resolve()
    index_file = (dist_root / "index.html").resolve()

    if index_file.parent != dist_root or not index_file.is_file():
        logger.error(
            "Frontend build entry point not found: %s",
            index_file,
        )
        raise HTTPException(
            status_code=503,
            detail=(
                "PageTrail frontend build is unavailable. "
                "Build the frontend so frontend/dist/index.html exists."
            ),
        )

    return index_file


@app.get("/", include_in_schema=False)
async def root() -> FileResponse:
    """Serve the React app at / instead of redirecting to /login."""
    return FileResponse(
        _frontend_index(),
        media_type="text/html",
    )


def _frontend_file(path: str) -> Path | None:
    """Resolve frontend files without allowing path traversal."""
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
            return FileResponse(
                candidate,
                media_type="image/png",
            )

    raise HTTPException(
        status_code=404,
        detail="Icon not found.",
    )


if FRONTEND_DIST.exists():
    assets = FRONTEND_DIST / "assets"

    if assets.is_dir():
        app.mount(
            "/assets",
            StaticFiles(directory=assets),
            name="assets",
        )

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str) -> FileResponse:
        # Unknown API routes should return 404, not frontend HTML.
        if path == "api" or path.startswith("api/"):
            raise HTTPException(
                status_code=404,
                detail="API endpoint not found.",
            )

        # Serve existing files such as icons and manifests.
        requested = _frontend_file(path)

        if requested is not None:
            return FileResponse(requested)

        # Let React handle frontend routes such as /login and /features.
        return FileResponse(
            _frontend_index(),
            media_type="text/html",
        )


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", "10000")),
        reload=False,
        log_level="info",
    )
