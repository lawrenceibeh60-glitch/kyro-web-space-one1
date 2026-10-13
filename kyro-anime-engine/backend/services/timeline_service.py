"""Timeline + JSON-script operations for keyframe editing."""
from backend.app.exceptions import ApiError
from backend.services.validation_service import validate_project
from backend.storage import project_repository as repo

CHANNELS = {"x", "y", "rotation", "scale_x", "scale_y", "opacity"}


def _project(pid):
    return repo.load(pid)


def _save(pid, project):
    errs = validate_project(project)
    if errs:
        raise ApiError(422, "Project failed validation", errs)
    project["modified"] = project.get("modified", "")
    repo.save(pid, project)
    return project


def _find_layer(project, scene_id, layer_id):
    for scene in project.get("scenes", []):
        if scene.get("id") != scene_id:
            continue
        for layer in scene.get("layers", []):
            if layer.get("id") == layer_id:
                return scene, layer
    raise ApiError(404, f"Layer '{layer_id}' not found in scene '{scene_id}'")


def timeline_summary(pid):
    project = _project(pid)
    settings = project.get("settings", {})
    return {
        "project_id": project.get("id"),
        "fps": settings.get("fps", 12),
        "frames": settings.get("duration_frames", 24),
        "scene_count": len(project.get("scenes", [])),
        "layer_count": sum(len(scene.get("layers", [])) for scene in project.get("scenes", [])),
    }


def _set_keyframe(project, payload):
    scene_id = payload.get("scene_id")
    layer_id = payload.get("layer_id")
    channel = payload.get("channel")
    if channel not in CHANNELS:
        raise ApiError(400, f"channel must be one of {sorted(CHANNELS)}")
    time = payload.get("time")
    if not isinstance(time, int) or time < 0:
        raise ApiError(400, "time must be a non-negative integer")
    _, layer = _find_layer(project, scene_id, layer_id)
    tracks = layer.setdefault("tracks", {})
    keyframes = tracks.setdefault(channel, [])
    if not isinstance(keyframes, list):
        raise ApiError(400, f"channel '{channel}' is not a valid keyframe list")
    for k in keyframes:
        if k.get("t") == time:
            k["v"] = payload.get("value")
            k["ease"] = payload.get("ease", "linear")
            return k
    keyframes.append({"t": time, "v": payload.get("value"), "ease": payload.get("ease", "linear")})
    keyframes.sort(key=lambda item: item.get("t", 0))
    return keyframes[-1]


def set_keyframe(pid, payload):
    if not isinstance(payload, dict):
        raise ApiError(400, "Keyframe payload must be an object")
    project = _project(pid)
    keyframe = _set_keyframe(project, payload)
    _save(pid, project)
    return keyframe


def _delete_keyframe(project, payload):
    _, layer = _find_layer(project, payload.get("scene_id"), payload.get("layer_id"))
    channel = payload.get("channel")
    key_time = payload.get("time")
    tracks = layer.get("tracks", {})
    if channel not in tracks:
        raise ApiError(404, f"Channel '{channel}' has no keyframes")
    index = next((i for i, k in enumerate(tracks[channel]) if k.get("t") == key_time), None)
    if index is None:
        raise ApiError(404, f"No keyframe at time {key_time} on channel '{channel}'")
    del tracks[channel][index]
    if not tracks[channel]:
        del tracks[channel]


def delete_keyframe(pid, payload):
    if not isinstance(payload, dict):
        raise ApiError(400, "Keyframe payload must be an object")
    project = _project(pid)
    _delete_keyframe(project, payload)
    _save(pid, project)


def apply_script(pid, script):
    if not isinstance(script, dict):
        raise ApiError(400, "Script must be a JSON object")
    ops = script.get("ops")
    if not isinstance(ops, list):
        raise ApiError(400, "Script must contain an 'ops' array")
    project = _project(pid)
    results = []
    for op in ops:
        if not isinstance(op, dict):
            raise ApiError(400, "Each script op must be an object")
        kind = op.get("op")
        if kind == "set_key":
            keyframe = _set_keyframe(project, op)
            results.append(dict(keyframe))
        elif kind == "delete_key":
            _delete_keyframe(project, op)
            results.append({"op": "delete_key", "ok": True})
        else:
            raise ApiError(400, f"Unsupported script op '{kind}'")
    if results:
        _save(pid, project)
    return {"applied": len(results), "results": results}
