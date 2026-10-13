"""backend/api/exports.py
GET  /api/exports/capabilities            {pillow, formats}
POST /api/exports                         start a job {project_id, format, frames, fps, ...}
PUT  /api/exports/<job>/frames/<index>    upload one PNG frame (raw body)
POST /api/exports/<job>/finish            encode -> {filename, size, url}
GET  /api/exports/<job>/download          download the result
"""
from flask import Blueprint, jsonify, request, send_file

from backend.app.exceptions import ApiError
from backend.services import export_service as svc

bp = Blueprint("exports", __name__)


@bp.get("/capabilities")
def capabilities():
    return jsonify(svc.capabilities())


@bp.post("")
def create_job():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError(400, "Request body must be a JSON object")
    return jsonify(svc.create_job(data)), 201


@bp.put("/<job_id>/frames/<int:index>")
def put_frame(job_id, index):
    svc.save_frame(job_id, index, request.get_data())
    return "", 204


@bp.post("/<job_id>/finish")
def finish(job_id):
    return jsonify(svc.finish(job_id))


@bp.get("/<job_id>/download")
def download(job_id):
    path, name = svc.output_file(job_id)
    return send_file(path, as_attachment=True, download_name=name)
