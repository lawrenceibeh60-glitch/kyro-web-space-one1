"""Global settings routes."""
from flask import Blueprint, jsonify, request

from backend.app.exceptions import ApiError
import config

bp = Blueprint("settings", __name__)


def _body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError(400, "Request body must be a JSON object")
    return data


@bp.get("/settings")
def get_settings():
    return jsonify({
        "app": {
            "name": "KYRO Anime Engine",
            "version": config.APP_VERSION,
            "format_version": config.FORMAT_VERSION,
            "debug": config.DEBUG,
        },
        "exports": {"formats": ["png", "gif", "sprite"], "max_frames": config.MAX_EXPORT_FRAMES},
    })


@bp.put("/settings")
def update_settings():
    payload = _body()
    return jsonify({"saved": True, "settings": payload})

