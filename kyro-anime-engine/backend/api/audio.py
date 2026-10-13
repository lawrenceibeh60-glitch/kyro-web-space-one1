"""Audio asset and timeline clip routes."""
from flask import Blueprint, jsonify, request, send_file

from backend.app.exceptions import ApiError
from backend.services import audio_service as svc

bp = Blueprint("audio", __name__)


@bp.get("/<pid>/audio")
def list_audio(pid):
    return jsonify(audio=svc.list_audio(pid))


@bp.post("/<pid>/audio")
def upload_audio(pid):
    uploaded = request.files.get("file")
    if uploaded is None:
        raise ApiError(400, "Multipart field 'file' is required")
    metadata = {
        "id": request.form.get("id"),
        "name": request.form.get("name"),
        "start_frame": request.form.get("start_frame", "0"),
        "offset_seconds": request.form.get("offset_seconds", "0"),
        "volume": request.form.get("volume", "1"),
    }
    return jsonify(svc.upload_audio(pid, uploaded, metadata)), 201


@bp.get("/<pid>/audio/<clip_id>")
def get_audio(pid, clip_id):
    path, mimetype, name = svc.audio_file(pid, clip_id)
    return send_file(path, mimetype=mimetype, download_name=name, conditional=True)


@bp.delete("/<pid>/audio/<clip_id>")
def delete_audio(pid, clip_id):
    svc.delete_audio(pid, clip_id)
    return "", 204
