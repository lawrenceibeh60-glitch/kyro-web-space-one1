"""Scene-level project operations."""
from flask import Blueprint, jsonify, request

from backend.app.exceptions import ApiError
from backend.services import scene_service as svc

bp = Blueprint("scenes", __name__)


def _body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError(400, "Request body must be a JSON object")
    return data


@bp.get("/<pid>/scenes")
def list_scenes(pid):
    return jsonify(scenes=svc.list_scenes(pid))


@bp.post("/<pid>/scenes")
def create_scene(pid):
    return jsonify(svc.create_scene(pid, _body())), 201


@bp.get("/<pid>/scenes/<scene_id>")
def get_scene(pid, scene_id):
    return jsonify(svc.get_scene(pid, scene_id))


@bp.put("/<pid>/scenes/<scene_id>")
def update_scene(pid, scene_id):
    return jsonify(svc.update_scene(pid, scene_id, _body()))


@bp.delete("/<pid>/scenes/<scene_id>")
def delete_scene(pid, scene_id):
    svc.delete_scene(pid, scene_id)
    return "", 204

