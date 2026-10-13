"""Load and validate a single scene from a KAE project."""
from copy import deepcopy
from engine.scenes.scene_validation import validate_scene


def load_scene(project, scene_id):
    scene = next((item for item in project.get("scenes", []) if item.get("id") == scene_id), None)
    if scene is None:
        raise KeyError(f"Scene not found: {scene_id}")
    errors = validate_scene(scene, project.get("drawings", {}))
    if errors:
        from engine.core.errors import ValidationError
        raise ValidationError(f"Scene {scene_id} failed validation", errors)
    return deepcopy(scene)
