"""Asset import and manifest helpers."""
from backend.app.exceptions import ApiError
from backend.storage import project_repository as repo


def _project(pid):
    return repo.load(pid)


def list_assets(pid):
    project = _project(pid)
    assets = []
    for key, drawing in (project.get("drawings", {}) or {}).items():
        assets.append({"id": drawing.get("id", key), "name": drawing.get("name", key), "kind": "drawing", "source": key})
    return assets


def import_asset(pid, payload):
    if not isinstance(payload, dict):
        raise ApiError(400, "Asset import payload must be an object")
    project = _project(pid)
    key = payload.get("id") or payload.get("name") or "imported_asset"
    project.setdefault("drawings", {})[key] = {
        "id": key,
        "name": payload.get("name", key),
        "strokes": payload.get("strokes", []),
    }
    project["modified"] = project.get("modified", "")
    repo.save(pid, project)
    return project["drawings"][key]

