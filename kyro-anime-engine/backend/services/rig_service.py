"""Persistent 2D character rigs."""
from copy import deepcopy

from backend.app.exceptions import ApiError
from backend.services.project_service import _now
from backend.services.validation_service import validate_project
from backend.storage import project_repository as repo


def _project(pid):
    return repo.load(pid)


def list_rigs(pid):
    return _project(pid).get("rigs", [])


def save_rig(pid, payload, rig_id=None):
    if not isinstance(payload, dict):
        raise ApiError(400, "Rig payload must be a JSON object")
    project = _project(pid)
    rigs = project.setdefault("rigs", [])
    data = {**payload, "id": rig_id or payload.get("id") or f"rig_{len(rigs) + 1}"}
    if "bones" not in data:
        data["bones"] = []
    index = next((i for i, item in enumerate(rigs) if item.get("id") == data["id"]), -1)
    previous = deepcopy(rigs[index]) if index >= 0 else None
    if index < 0:
        rigs.append(data)
    else:
        rigs[index] = data
    errors = validate_project(project)
    if errors:
        if index < 0:
            rigs.pop()
        else:
            rigs[index] = previous
            raise ApiError(422, "Rig failed project validation", errors)
        raise ApiError(422, "Rig failed project validation", errors)
    project["modified"] = _now()
    repo.save(pid, project)
    return data


def delete_rig(pid, rig_id):
    project = _project(pid)
    rigs = project.get("rigs", [])
    index = next((i for i, item in enumerate(rigs) if item.get("id") == rig_id), -1)
    if index < 0:
        raise ApiError(404, f"Rig '{rig_id}' not found")
    rigs.pop(index)
    project["modified"] = _now()
    repo.save(pid, project)
