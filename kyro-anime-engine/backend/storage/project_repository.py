"""Project storage facade: PostgreSQL in production, atomic JSON files locally."""
import shutil
import threading

import config
from backend.app.exceptions import ApiError
from backend.storage.atomic_writer import read_json, write_json_atomic
from backend.storage.file_manager import safe_id
from backend.storage import postgres_projects

_lock = threading.Lock()


def _dir(pid):
    return config.PROJECTS_DIR / safe_id(pid)


def _file(pid):
    return _dir(pid) / "project.json"


def backend_name():
    return "postgresql" if postgres_projects.configured() else "filesystem"


def exists(pid):
    pid = safe_id(pid)
    if postgres_projects.configured():
        return postgres_projects.exists(pid)
    return _file(pid).exists()


def list_ids():
    if postgres_projects.configured():
        return postgres_projects.list_ids()
    root = config.PROJECTS_DIR
    if not root.exists():
        return []
    return sorted(p.name for p in root.iterdir() if (p / "project.json").exists())


def load(pid):
    pid = safe_id(pid)
    if postgres_projects.configured():
        document = postgres_projects.load(pid)
        if document is None:
            raise ApiError(404, f"Project '{pid}' not found")
        return document
    if not _file(pid).exists():
        raise ApiError(404, f"Project '{pid}' not found")
    return read_json(_file(pid))


def save(pid, data):
    pid = safe_id(pid)
    if postgres_projects.configured():
        postgres_projects.save(pid, data)
        return
    with _lock:
        write_json_atomic(_file(pid), data)


def delete(pid):
    pid = safe_id(pid)
    if postgres_projects.configured():
        if not postgres_projects.delete(pid):
            raise ApiError(404, f"Project '{pid}' not found")
        return
    if not _file(pid).exists():
        raise ApiError(404, f"Project '{pid}' not found")
    with _lock:
        shutil.rmtree(_dir(pid))
