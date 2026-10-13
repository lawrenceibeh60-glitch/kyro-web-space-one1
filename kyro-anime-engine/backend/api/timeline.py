"""Timeline and keyframe scripting routes."""
from flask import Blueprint, jsonify, request

from backend.app.exceptions import ApiError
from backend.services import timeline_service as svc

bp = Blueprint("timeline", __name__)


def _body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError(400, "Request body must be a JSON object")
    return data


@bp.get("/<pid>/timeline")
def timeline(pid):
    return jsonify(svc.timeline_summary(pid))


@bp.post("/<pid>/timeline/keyframe")
def set_keyframe(pid):
    return jsonify(svc.set_keyframe(pid, _body())), 201


@bp.delete("/<pid>/timeline/keyframe")
def delete_keyframe(pid):
    data = _body()
    svc.delete_keyframe(pid, data)
    return "", 204


@bp.post("/<pid>/timeline/script")
def apply_script(pid):
    return jsonify(svc.apply_script(pid, _body()))

