"""backend/api/health.py"""
from flask import Blueprint, jsonify

import config

bp = Blueprint("health", __name__)


@bp.get("/health")
def health():
    return jsonify(status="ok", app="kae", version=config.APP_VERSION, format_version=config.FORMAT_VERSION)


@bp.get("/health/storage")
def storage_health():
    """Report persistence configuration without exposing credentials or project data."""
    from backend.storage import postgres_projects, project_repository

    configured = postgres_projects.configured()
    if not configured:
        return jsonify(
            status="degraded",
            storage="filesystem",
            durable=False,
            message="DATABASE_URL is not configured; Render filesystem storage is ephemeral.",
        ), 503
    try:
        postgres_projects.check_connection()
    except Exception:
        # Deliberately avoid returning database errors, hostnames, or connection details.
        return jsonify(
            status="error", storage="postgresql", durable=True,
            message="PostgreSQL is configured but the connection check failed.",
        ), 503
    return jsonify(
        status="ok", storage=project_repository.backend_name(), durable=True,
        message="PostgreSQL connection is healthy.",
    )
