"""Drawing import and mutation helpers."""
from backend.app.exceptions import ApiError
from backend.services.validation_service import validate_project
from backend.storage import project_repository as repo
from backend.services.schema_validator import validator


def _project(pid):
    return repo.load(pid)


def _save(pid, project):
    errs = validate_project(project)
    if errs:
        raise ApiError(422, "Project failed validation", errs)
    project["modified"] = project.get("modified", "")
    repo.save(pid, project)
    return project


def list_drawings(pid):
    return _project(pid).get("drawings", {})


def get_drawing(pid, drawing_id):
    project = _project(pid)
    drawing = project.get("drawings", {}).get(drawing_id)
    if drawing is None:
        raise ApiError(404, f"Drawing '{drawing_id}' not found")
    return drawing


def create_drawing(pid, payload):
    project = _project(pid)
    drawings = project.setdefault("drawings", {})
    data = payload or {}
    if not isinstance(data, dict):
        raise ApiError(400, "Drawing payload must be an object")
    
    # Validate the drawing against the schema
    is_valid, error = validator.validate_drawing(data)
    if not is_valid:
        raise ApiError(400, f"Invalid drawing data: {error}")
    
    drawing_id = data.get("id") or f"drawing_{len(drawings) + 1}"
    drawing = {"id": drawing_id, "name": data.get("name", drawing_id), "strokes": data.get("strokes", [])}
    drawings[drawing_id] = drawing
    return _save(pid, project)["drawings"][drawing_id]


def update_drawing(pid, drawing_id, payload):
    project = _project(pid)
    drawings = project.get("drawings", {})
    if drawing_id not in drawings:
        raise ApiError(404, f"Drawing '{drawing_id}' not found")
    
    # Validate the updated drawing against the schema
    updated_drawing = {**drawings[drawing_id], **(payload or {})}
    is_valid, error = validator.validate_drawing(updated_drawing)
    if not is_valid:
        raise ApiError(400, f"Invalid drawing data: {error}")
    
    drawings[drawing_id] = updated_drawing
    return _save(pid, project)["drawings"][drawing_id]


def delete_drawing(pid, drawing_id):
    project = _project(pid)
    drawings = project.get("drawings", {})
    if drawing_id not in drawings:
        raise ApiError(404, f"Drawing '{drawing_id}' not found")
    del drawings[drawing_id]
    _save(pid, project)


def import_drawing(pid, payload):
    if not isinstance(payload, dict):
        raise ApiError(400, "Import payload must be a JSON object")
    return create_drawing(pid, payload)

