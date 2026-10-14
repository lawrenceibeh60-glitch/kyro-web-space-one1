"""config.py - central settings. Override with env vars (KAE_PROJECTS_DIR, KAE_HOST, KAE_PORT, KAE_DEBUG)."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECTS_DIR = Path(os.environ.get("KAE_PROJECTS_DIR", BASE_DIR / "projects"))
FRONTEND_DIR = BASE_DIR / "frontend"
SCHEMAS_DIR = BASE_DIR / "formats" / "schemas"
EXPORTS_DIR = Path(os.environ.get("KAE_EXPORTS_DIR", BASE_DIR / "exports"))

HOST = os.environ.get("KAE_HOST", "127.0.0.1")
PORT = int(os.environ.get("KAE_PORT", "5000"))
DEBUG = os.environ.get("KAE_DEBUG", "1") == "1"

MAX_CONTENT_LENGTH = 64 * 1024 * 1024
FORMAT_VERSION = 2
MAX_EXPORT_FRAMES = 2000
EXPORT_TTL_HOURS = 24  # old export jobs are deleted when a new one starts
APP_VERSION = "0.1.0"
