"""Layer-level project operations."""
from flask import Blueprint, jsonify, request

from backend.app.exceptions import ApiError
from backend.services import scene_service as svc

bp = Blueprint("layers", __name__)


def _body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError(400, "Request body must be a JSON object")
    return data


@bp.get("/<pid>/scenes/<scene_id>/layers")
def list_layers(pid, scene_id):
    return jsonify(layers=svc.list_layers(pid, scene_id))


@bp.post("/<pid>/scenes/<scene_id>/layers")
def add_layer(pid, scene_id):
    return jsonify(svc.add_layer(pid, scene_id, _body())), 201


@bp.get("/<pid>/scenes/<scene_id>/layers/<layer_id>")
def get_layer(pid, scene_id, layer_id):
    return jsonify(svc.get_layer(pid, scene_id, layer_id))


@bp.put("/<pid>/scenes/<scene_id>/layers/<layer_id>")
def update_layer(pid, scene_id, layer_id):
    return jsonify(svc.update_layer(pid, scene_id, layer_id, _body()))


@bp.delete("/<pid>/scenes/<scene_id>/layers/<layer_id>")
def delete_layer(pid, scene_id, layer_id):
    svc.delete_layer(pid, scene_id, layer_id)
    return "", 204

