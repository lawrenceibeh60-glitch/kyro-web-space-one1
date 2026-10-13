"""Render summary and effect helpers."""
from copy import deepcopy

from backend.app.exceptions import ApiError
from backend.services.project_service import _now
from backend.services.validation_service import validate_project
from backend.storage import project_repository as repo


def _project(pid):
    return repo.load(pid)


def render_summary(pid):
    project = _project(pid)
    settings = project.get("settings", {})
    scenes = project.get("scenes", [])
    return {
        "project_id": project.get("id"),
        "width": settings.get("width", 1280),
        "height": settings.get("height", 720),
        "fps": settings.get("fps", 12),
        "duration_frames": settings.get("duration_frames", 24),
        "scene_count": len(scenes),
        "layer_count": sum(len(scene.get("layers", [])) for scene in scenes),
    }


def list_effects(pid):
    return _project(pid).get("effects", [])


def add_effect(pid, payload):
    project = _project(pid)
    effects = project.setdefault("effects", [])
    data = payload or {}
    if not isinstance(data, dict):
        raise ApiError(400, "Effect payload must be a JSON object")
    scenes = project.get("scenes", [])
    if not isinstance(scenes, list) or not scenes or not isinstance(scenes[0], dict) or not scenes[0].get("id"):
        raise ApiError(422, "A scene is required before adding an effect")
    effect_id = data.get("id") or f"fx_{len(effects) + 1}"
    effect = {
        "id": effect_id,
        "scene_id": data.get("scene_id") or scenes[0].get("id"),
        "type": data.get("type", "lightning"),
        "enabled": data.get("enabled", True),
        "start_frame": data.get("start_frame", 0),
        "end_frame": data.get("end_frame", project["settings"]["duration_frames"] - 1),
        "intensity": data.get("intensity", 0.5),
        "color": data.get("color", "#ffffff"),
        "count": data.get("count", 36),
        "speed": data.get("speed", 1),
    }
    index = next((i for i, item in enumerate(effects) if item.get("id") == effect_id), -1)
    previous = deepcopy(effects[index]) if index >= 0 else None
    if index >= 0:
        effects[index] = effect
    else:
        effects.append(effect)
    errors = validate_project(project)
    if errors:
        if previous is None:
            effects.pop()
        else:
            effects[index] = previous
        raise ApiError(422, "Effect failed project validation", errors)
    project["modified"] = _now()
    repo.save(pid, project)
    return effect


def delete_effect(pid, effect_id):
    project = _project(pid)
    effects = project.get("effects", [])
    index = next((i for i, item in enumerate(effects) if item.get("id") == effect_id), -1)
    if index < 0:
        raise ApiError(404, f"Effect '{effect_id}' not found")
    effects.pop(index)
    project["modified"] = _now()
    repo.save(pid, project)
