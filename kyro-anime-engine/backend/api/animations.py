"""Animation clip routes."""
from flask import Blueprint, jsonify, request

from backend.app.exceptions import ApiError
from backend.services import animation_service as svc

bp = Blueprint("animations", __name__)


def _body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError(400, "Request body must be a JSON object")
    return data


@bp.get("/<pid>/animations")
def list_animations(pid):
    return jsonify(animations=svc.list_animations(pid))


@bp.post("/<pid>/animations")
def create_animation(pid):
    return jsonify(svc.create_animation(pid, _body())), 201


@bp.get("/<pid>/animations/<clip_id>")
def get_animation(pid, clip_id):
    return jsonify(svc.get_animation(pid, clip_id))

