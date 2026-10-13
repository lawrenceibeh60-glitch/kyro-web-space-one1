"""Drawing CRUD plus import helpers."""
from flask import Blueprint, jsonify, request

from backend.app.exceptions import ApiError
from backend.services import drawing_service as svc

bp = Blueprint("drawings", __name__)


def _body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError(400, "Request body must be a JSON object")
    return data


@bp.get("/<pid>/drawings")
def list_drawings(pid):
    return jsonify(drawings=svc.list_drawings(pid))


@bp.post("/<pid>/drawings")
def create_drawing(pid):
    return jsonify(svc.create_drawing(pid, _body())), 201


@bp.get("/<pid>/drawings/<drawing_id>")
def get_drawing(pid, drawing_id):
    return jsonify(svc.get_drawing(pid, drawing_id))


@bp.put("/<pid>/drawings/<drawing_id>")
def update_drawing(pid, drawing_id):
    return jsonify(svc.update_drawing(pid, drawing_id, _body()))


@bp.delete("/<pid>/drawings/<drawing_id>")
def delete_drawing(pid, drawing_id):
    svc.delete_drawing(pid, drawing_id)
    return "", 204


@bp.post("/<pid>/drawings/import")
def import_drawing(pid):
    return jsonify(svc.import_drawing(pid, _body())), 201

