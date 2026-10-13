"""Scene and layer operations for KAE projects."""
from backend.app.exceptions import ApiError
from backend.services.validation_service import validate_project
from backend.storage import project_repository as repo


def _project(pid):
    return repo.load(pid)


def _save(pid, project):
    project["modified"] = project.get("modified", "")
    errs = validate_project(project)
    if errs:
        raise ApiError(422, "Project failed validation", errs)
    repo.save(pid, project)
    return project


def list_scenes(pid):
    return _project(pid).get("scenes", [])


def _find_scene(project, scene_id):
    for scene in project.get("scenes", []):
        if scene.get("id") == scene_id:
            return scene
    raise ApiError(404, f"Scene '{scene_id}' not found")


def get_scene(pid, scene_id):
    return _find_scene(_project(pid), scene_id)


def create_scene(pid, payload):
    project = _project(pid)
    scene = payload or {}
    if not isinstance(scene, dict):
        raise ApiError(400, "Scene must be a JSON object")
    scene_id = scene.get("id") or f"scene_{len(project.get('scenes', [])) + 1}"
    scene.setdefault("name", f"Scene {len(project.get('scenes', [])) + 1}")
    scene["id"] = scene_id
    scene.setdefault("camera", {"transform": {"x": 0, "y": 0, "scale_x": 1, "scale_y": 1}, "tracks": {}})
    scene.setdefault("layers", [])
    project.setdefault("scenes", []).append(scene)
    return _save(pid, project)["scenes"][-1]


def update_scene(pid, scene_id, payload):
    project = _project(pid)
    for index, scene in enumerate(project.get("scenes", [])):
        if scene.get("id") == scene_id:
            project["scenes"][index] = {**scene, **(payload or {})}
            return _save(pid, project)["scenes"][index]
    raise ApiError(404, f"Scene '{scene_id}' not found")


def delete_scene(pid, scene_id):
    project = _project(pid)
    scenes = project.get("scenes", [])
    keep = [scene for scene in scenes if scene.get("id") != scene_id]
    if len(keep) == len(scenes):
        raise ApiError(404, f"Scene '{scene_id}' not found")
    project["scenes"] = keep
    _save(pid, project)


def list_layers(pid, scene_id):
    return get_scene(pid, scene_id).get("layers", [])


def get_layer(pid, scene_id, layer_id):
    for layer in list_layers(pid, scene_id):
        if layer.get("id") == layer_id:
            return layer
    raise ApiError(404, f"Layer '{layer_id}' not found")


def add_layer(pid, scene_id, payload):
    project = _project(pid)
    scene = _find_scene(project, scene_id)
    layer = payload or {}
    if not isinstance(layer, dict):
        raise ApiError(400, "Layer must be a JSON object")
    layer_id = layer.get("id") or f"layer_{len(scene.get('layers', [])) + 1}"
    layer.setdefault("name", f"Layer {len(scene.get('layers', [])) + 1}")
    layer.setdefault("type", "drawing")
    layer["id"] = layer_id
    layer.setdefault("tracks", {})
    layer.setdefault("exposures", [])
    scene.setdefault("layers", []).append(layer)
    _save(pid, project)
    return scene["layers"][-1]


def update_layer(pid, scene_id, layer_id, payload):
    project = _project(pid)
    scene = _find_scene(project, scene_id)
    layers = scene.get("layers", [])
    for index, layer in enumerate(layers):
        if layer.get("id") == layer_id:
            layers[index] = {**layer, **(payload or {})}
            _save(pid, project)
            return layers[index]
    raise ApiError(404, f"Layer '{layer_id}' not found")


def delete_layer(pid, scene_id, layer_id):
    project = _project(pid)
    scene = _find_scene(project, scene_id)
    layers = scene.get("layers", [])
    kept = [layer for layer in layers if layer.get("id") != layer_id]
    if len(kept) == len(layers):
        raise ApiError(404, f"Layer '{layer_id}' not found")
    scene["layers"] = kept
    _save(pid, project)


def get_camera(pid, scene_id):
    return get_scene(pid, scene_id).get("camera", {"transform": {"x": 0, "y": 0, "scale_x": 1, "scale_y": 1}, "tracks": {}})


def update_camera(pid, scene_id, payload):
    project = _project(pid)
    for scene in project.get("scenes", []):
        if scene.get("id") == scene_id:
            scene["camera"] = payload or scene.get("camera")
            _save(pid, project)
            return scene["camera"]
    raise ApiError(404, f"Scene '{scene_id}' not found")
