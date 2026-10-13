"""Project-scoped audio clip storage and metadata."""
import os
import re
import uuid

import config
from backend.app.exceptions import ApiError
from backend.services.project_service import _now
from backend.services.validation_service import validate_project
from backend.storage import project_repository as repo
from backend.storage.file_manager import safe_id

AUDIO_TYPES = {
    ".aac": "audio/aac",
    ".m4a": "audio/mp4",
    ".mp3": "audio/mpeg",
    ".ogg": "audio/ogg",
    ".wav": "audio/wav",
    ".webm": "audio/webm",
}


def _audio_dir(pid):
    return config.PROJECTS_DIR / safe_id(pid) / "audio"


def _stored_path(pid, clip):
    filename = clip.get("filename", "")
    if not isinstance(filename, str) or not isinstance(clip.get("id"), str):
        raise ApiError(422, "Audio clip contains an invalid stored file reference")
    extension = os.path.splitext(filename)[1].lower()
    if (
        extension not in AUDIO_TYPES
        or filename != f"{clip.get('id')}{extension}"
        or clip.get("mime_type") != AUDIO_TYPES[extension]
    ):
        raise ApiError(422, "Audio clip contains an invalid stored file reference")
    return _audio_dir(pid) / filename


def list_audio(pid):
    return repo.load(pid).get("audio", [])


def upload_audio(pid, uploaded, metadata):
    if not isinstance(metadata, dict):
        raise ApiError(400, "Audio metadata must be a JSON object")
    if uploaded is None or not uploaded.filename:
        raise ApiError(400, "Select an audio file to upload")
    extension = os.path.splitext(uploaded.filename)[1].lower()
    if extension not in AUDIO_TYPES:
        raise ApiError(415, "Supported audio files: WAV, MP3, OGG, M4A, AAC, and WebM")
    data = uploaded.read(config.MAX_CONTENT_LENGTH + 1)
    if not data:
        raise ApiError(400, "Audio file is empty")
    if len(data) > config.MAX_CONTENT_LENGTH:
        raise ApiError(413, "Audio file exceeds the upload limit")

    project = repo.load(pid)
    clip_id = metadata.get("id") or f"audio_{uuid.uuid4().hex[:16]}"
    if not isinstance(clip_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", clip_id):
        raise ApiError(400, "Audio clip id is invalid")
    try:
        start_frame = int(metadata.get("start_frame", 0))
        offset_seconds = float(metadata.get("offset_seconds", 0))
        volume = float(metadata.get("volume", 1))
    except (TypeError, ValueError):
        raise ApiError(400, "Audio timing and volume must be numeric")
    name = metadata.get("name") or os.path.basename(uploaded.filename)
    if not isinstance(name, str) or not name.strip() or len(name) > 160:
        raise ApiError(400, "Audio clip name must contain 1..160 characters")

    clip = {
        "id": clip_id,
        "name": name.strip(),
        "filename": f"{clip_id}{extension}",
        "mime_type": AUDIO_TYPES[extension],
        "url": f"/api/projects/{safe_id(pid)}/audio/{clip_id}",
        "start_frame": start_frame,
        "offset_seconds": offset_seconds,
        "volume": volume,
    }
    clips = project.setdefault("audio", [])
    old_index = next((i for i, item in enumerate(clips) if item.get("id") == clip_id), -1)
    previous = clips[old_index] if old_index >= 0 else None
    if old_index >= 0:
        clips[old_index] = clip
    else:
        clips.append(clip)
    errors = validate_project(project)
    if errors:
        if previous is None:
            clips.pop()
        else:
            clips[old_index] = previous
        raise ApiError(422, "Audio clip failed project validation", errors)

    directory = _audio_dir(pid)
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / clip["filename"]
    temporary = directory / f".{clip_id}.upload"
    try:
        temporary.write_bytes(data)
        os.replace(temporary, destination)
    except OSError as error:
        temporary.unlink(missing_ok=True)
        raise ApiError(500, f"Could not store audio file: {error}")
    project["modified"] = _now()
    repo.save(pid, project)
    if previous and previous.get("filename") != clip["filename"]:
        _stored_path(pid, previous).unlink(missing_ok=True)
    return {"clip": clip, "project": project}


def audio_file(pid, clip_id):
    clip = next((item for item in list_audio(pid) if item.get("id") == clip_id), None)
    if clip is None:
        raise ApiError(404, f"Audio clip '{clip_id}' not found")
    path = _stored_path(pid, clip)
    if not path.is_file():
        raise ApiError(404, f"Audio data for clip '{clip_id}' is missing")
    return path, clip["mime_type"], clip["name"]


def delete_audio(pid, clip_id):
    project = repo.load(pid)
    clips = project.get("audio", [])
    index = next((i for i, item in enumerate(clips) if item.get("id") == clip_id), -1)
    if index < 0:
        raise ApiError(404, f"Audio clip '{clip_id}' not found")
    path = _stored_path(pid, clips[index])
    clip = clips.pop(index)
    project["modified"] = _now()
    repo.save(pid, project)
    path.unlink(missing_ok=True)
