"""Asset manifest routes."""
from flask import Blueprint, jsonify, request

from backend.app.exceptions import ApiError
from backend.services import asset_service as svc

bp = Blueprint("assets", __name__)


def _body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError(400, "Request body must be a JSON object")
    return data


@bp.get("/<pid>/assets")
def list_assets(pid):
    return jsonify(assets=svc.list_assets(pid))


@bp.post("/<pid>/assets/import")
def import_asset(pid):
    return jsonify(svc.import_asset(pid, _body())), 201

