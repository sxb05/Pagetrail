from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = APP_DIR.parent
REPO_ROOT = BACKEND_DIR.parent

FRONTEND_DIR = REPO_ROOT / "frontend"
FRONTEND_DIST = FRONTEND_DIR / "dist"
FRONTEND_PUBLIC = FRONTEND_DIR / "public"
BRAND_ICON = FRONTEND_DIR / "pagetrail-icon.png"
UPLOAD_DIR = REPO_ROOT / "uploads"
DATA_DIR = REPO_ROOT / "data"
