"""backend/api/health.py"""
from flask import Blueprint, jsonify

import config
from backend.storage import project_repository

bp = Blueprint("health", __name__)


@bp.get("/health")
def health():
    return jsonify(status="ok", app="kae", version=config.APP_VERSION, format_version=config.FORMAT_VERSION, storage_backend=project_repository.backend_name())
