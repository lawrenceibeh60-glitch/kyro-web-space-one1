"""Effect stack routes."""
from flask import Blueprint, jsonify, request

from backend.app.exceptions import ApiError
from backend.services import render_service as svc

bp = Blueprint("effects", __name__)


def _body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError(400, "Request body must be a JSON object")
    return data


@bp.get("/<pid>/effects")
def list_effects(pid):
    return jsonify(effects=svc.list_effects(pid))


@bp.post("/<pid>/effects")
def add_effect(pid):
    return jsonify(svc.add_effect(pid, _body())), 201


@bp.put("/<pid>/effects/<effect_id>")
def update_effect(pid, effect_id):
    data = _body()
    data["id"] = effect_id
    return jsonify(svc.add_effect(pid, data))


@bp.delete("/<pid>/effects/<effect_id>")
def delete_effect(pid, effect_id):
    svc.delete_effect(pid, effect_id)
    return "", 204
