"""Render preview/access routes."""
from flask import Blueprint, jsonify

from backend.services import render_service as svc

bp = Blueprint("rendering", __name__)


@bp.get("/<pid>/render")
def render_summary(pid):
    return jsonify(svc.render_summary(pid))

