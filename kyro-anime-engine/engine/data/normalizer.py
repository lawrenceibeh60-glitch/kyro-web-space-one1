"""Normalize optional KAE project fields without discarding user data."""
from copy import deepcopy
from engine.core.errors import ValidationError

DEFAULT_SETTINGS = {"width": 1280, "height": 720, "fps": 12, "duration_frames": 24, "background": "#ffffff"}


def normalize_project(project):
    if not isinstance(project, dict):
        raise ValidationError("Project must be a JSON object")
    result = deepcopy(project)
    result.setdefault("format", "kae")
    result.setdefault("version", 1)
    result.setdefault("name", "Untitled")
    if "settings" not in result:
        settings = {}
    else:
        settings = result["settings"]
    if not isinstance(settings, dict):
        raise ValidationError("settings must be an object")
    result["settings"] = {**DEFAULT_SETTINGS, **settings}
    result.setdefault("drawings", {})
    result.setdefault("scenes", [])
    result.setdefault("palette", [])
    result.setdefault("characters", [])
    result.setdefault("effects", [])
    result.setdefault("rigs", [])
    result.setdefault("audio", [])
    result.setdefault("styles", [])
    if not isinstance(result["scenes"], list):
        raise ValidationError("scenes must be a list")
    for scene in result["scenes"]:
        if isinstance(scene, dict):
            scene.setdefault("layers", [])
            scene.setdefault("camera", {
                "transform": {"x": 0, "y": 0, "scale_x": 1, "scale_y": 1},
                "tracks": {},
            })
    return result
