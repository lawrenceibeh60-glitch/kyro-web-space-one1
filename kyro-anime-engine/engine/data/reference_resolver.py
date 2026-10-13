"""Resolve and inspect KAE references between scenes, drawings, and characters."""
from engine.core.errors import ValidationError


def resolve_drawing(project, drawing_id, *, required=True):
    drawings = project.get("drawings", {})
    drawing = drawings.get(drawing_id) if isinstance(drawings, dict) else None
    if drawing is None and required:
        raise ValidationError(f"Drawing not found: {drawing_id}")
    return drawing


def resolve_scene(project, scene_id, *, required=True):
    scene = next((item for item in project.get("scenes", []) if item.get("id") == scene_id), None)
    if scene is None and required:
        raise ValidationError(f"Scene not found: {scene_id}")
    return scene


def iter_references(project):
    for scene in project.get("scenes", []):
        scene_id = scene.get("id")
        for layer in scene.get("layers", []):
            for exposure in layer.get("exposures", []):
                yield {"kind": "drawing", "source": f"{scene_id}/{layer.get('id')}", "target": exposure.get("drawing")}


def validate_references(project):
    drawings = project.get("drawings", {})
    return [
        f"{reference['source']}: drawing '{reference['target']}' not found"
        for reference in iter_references(project)
        if reference["target"] not in drawings
    ]
