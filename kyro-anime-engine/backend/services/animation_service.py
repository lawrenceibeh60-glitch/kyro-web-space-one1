"""Basic animation clip helpers."""
from backend.app.exceptions import ApiError
from backend.services.validation_service import validate_project
from backend.storage import project_repository as repo


def _project(pid):
    return repo.load(pid)


def list_animations(pid):
    return _project(pid).get("animations", [])


def get_animation(pid, clip_id):
    for clip in list_animations(pid):
        if clip.get("id") == clip_id:
            return clip
    raise ApiError(404, f"Animation '{clip_id}' not found")


def create_animation(pid, payload):
    project = _project(pid)
    anims = project.setdefault("animations", [])
    clip = payload or {}
    if not isinstance(clip, dict):
        raise ApiError(400, "Animation must be a JSON object")
    clip["id"] = clip.get("id") or f"clip_{len(anims) + 1}"
    clip.setdefault("name", clip["id"])
    clip.setdefault("start", 0)
    clip.setdefault("end", max(project.get("settings", {}).get("duration_frames", 24), 1))
    anims.append(clip)
    errs = validate_project(project)
    if errs:
        raise ApiError(422, "Project failed validation", errs)
    project["modified"] = project.get("modified", "")
    repo.save(pid, project)
    return clip

