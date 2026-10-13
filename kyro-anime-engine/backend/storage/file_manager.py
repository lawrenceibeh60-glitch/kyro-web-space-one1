"""backend/storage/file_manager.py - safe path helpers."""
import re

from backend.app.exceptions import ApiError

ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def safe_id(value):
    if not isinstance(value, str) or not ID_RE.match(value):
        raise ApiError(400, "Invalid id (use letters, digits, _ or -; max 64)")
    return value
