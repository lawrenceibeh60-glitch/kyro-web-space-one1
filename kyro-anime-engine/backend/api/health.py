"""Application and persistence health endpoints."""
from flask import Blueprint, jsonify

import config

bp = Blueprint("health", __name__)


@bp.get("/health")
def health():
    return jsonify(status="ok", app="kae", version=config.APP_VERSION, format_version=config.FORMAT_VERSION)


@bp.get("/health/storage")
def storage_health():
    """Report project and binary-asset durability without exposing credentials."""
    from backend.storage import object_storage, postgres_projects, project_repository

    database_configured = postgres_projects.configured()
    if not database_configured:
        return jsonify(
            status="degraded", projects_storage="filesystem",
            projects_durable=False, binary_assets_storage=(
                "object-storage" if object_storage.configured() else "filesystem"
            ), binary_assets_durable=object_storage.configured(),
            message="DATABASE_URL is not configured; Render filesystem project storage is ephemeral.",
        ), 503

    try:
        postgres_projects.check_connection()
    except Exception:
        return jsonify(
            status="error", projects_storage="postgresql", projects_durable=False,
            binary_assets_storage="object-storage" if object_storage.configured() else "filesystem",
            binary_assets_durable=False,
            message="PostgreSQL is configured but the connection check failed.",
        ), 503

    assets_configured = object_storage.configured()
    if assets_configured:
        try:
            object_storage.check_connection()
        except Exception:
            return jsonify(
                status="error", projects_storage="postgresql", projects_durable=True,
                binary_assets_storage="object-storage", binary_assets_durable=False,
                message="PostgreSQL is healthy, but object storage connectivity failed.",
            ), 503

    return jsonify(
        status="ok" if assets_configured else "degraded",
        projects_storage=project_repository.backend_name(),
        projects_durable=True,
        binary_assets_storage="object-storage" if assets_configured else "filesystem",
        binary_assets_durable=assets_configured,
        message=(
            "Project documents and configured binary assets are reachable."
            if assets_configured else
            "Project documents use PostgreSQL; uploaded binary assets still use the ephemeral filesystem."
        ),
    ), 200 if assets_configured else 503
