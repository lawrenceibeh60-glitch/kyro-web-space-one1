"""Rig routes."""
from flask import Blueprint, jsonify, request

from backend.app.exceptions import ApiError
from backend.services import rig_service as svc

bp = Blueprint("rigs", __name__)


def _body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError(400, "Request body must be a JSON object")
    return data


@bp.get("/<pid>/rigs")
def list_rigs(pid):
    return jsonify(rigs=svc.list_rigs(pid))


@bp.post("/<pid>/rigs")
def create_rig(pid):
    return jsonify(svc.save_rig(pid, _body())), 201


@bp.put("/<pid>/rigs/<rig_id>")
def update_rig(pid, rig_id):
    return jsonify(svc.save_rig(pid, _body(), rig_id))


@bp.delete("/<pid>/rigs/<rig_id>")
def delete_rig(pid, rig_id):
    svc.delete_rig(pid, rig_id)
    return "", 204
