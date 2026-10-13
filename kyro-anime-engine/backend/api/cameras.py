"""Camera operations."""
from flask import Blueprint, jsonify, request

from backend.app.exceptions import ApiError
from backend.services import scene_service as svc

bp = Blueprint("cameras", __name__)


def _body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError(400, "Request body must be a JSON object")
    return data


@bp.get("/<pid>/scenes/<scene_id>/camera")
def get_camera(pid, scene_id):
    return jsonify(svc.get_camera(pid, scene_id))


@bp.put("/<pid>/scenes/<scene_id>/camera")
def update_camera(pid, scene_id):
    return jsonify(svc.update_camera(pid, scene_id, _body()))

