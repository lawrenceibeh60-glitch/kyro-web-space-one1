"""Character routes."""
from flask import Blueprint, jsonify, request

from backend.app.exceptions import ApiError
from backend.services import character_service as svc

bp = Blueprint("characters", __name__)


def _body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError(400, "Request body must be a JSON object")
    return data


@bp.get("/<pid>/characters")
def list_characters(pid):
    return jsonify(characters=svc.list_characters(pid))


@bp.post("/<pid>/characters")
def create_character(pid):
    return jsonify(svc.create_character(pid, _body())), 201


@bp.post("/<pid>/characters/import")
def import_character(pid):
    return jsonify(svc.import_character(pid, _body())), 201


@bp.post("/<pid>/characters/generate")
def generate_character(pid):
    return jsonify(svc.generate_character(pid, _body())), 201
