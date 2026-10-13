"""backend/storage/project_repository.py - projects/<id>/project.json on disk."""
import shutil
import threading

import config
from backend.app.exceptions import ApiError
from backend.storage.atomic_writer import read_json, write_json_atomic
from backend.storage.file_manager import safe_id

_lock = threading.Lock()


def _dir(pid):
    return config.PROJECTS_DIR / safe_id(pid)


def _file(pid):
    return _dir(pid) / "project.json"


def exists(pid):
    return _file(pid).exists()


def list_ids():
    root = config.PROJECTS_DIR
    if not root.exists():
        return []
    return sorted(p.name for p in root.iterdir() if (p / "project.json").exists())


def load(pid):
    if not exists(pid):
        raise ApiError(404, f"Project '{pid}' not found")
    return read_json(_file(pid))


def save(pid, data):
    with _lock:
        write_json_atomic(_file(pid), data)


def delete(pid):
    if not exists(pid):
        raise ApiError(404, f"Project '{pid}' not found")
    with _lock:
        shutil.rmtree(_dir(pid))
