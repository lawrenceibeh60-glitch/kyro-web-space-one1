"""backend/services/export_service.py
Export pipeline: the browser renders frames (one renderer), uploads them as PNG, Python only encodes.
  create_job -> save_frame x N -> finish -> download
"""
import re
import shutil
import time
import uuid

import config
from backend.app.exceptions import ApiError
from backend.storage import project_repository as repo
from backend.storage.atomic_writer import read_json, write_json_atomic
from backend.storage.file_manager import safe_id
from engine.export import export_manager

FORMATS = ("png", "gif", "sprite")
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _dir(job_id):
    return config.EXPORTS_DIR / safe_id(job_id)


def _load(job_id):
    f = _dir(job_id) / "job.json"
    if not f.exists():
        raise ApiError(404, "Export job not found")
    return read_json(f)


def _slug(name):
    return re.sub(r"[^A-Za-z0-9]+", "_", str(name or "")).strip("_")[:40] or "animation"


def _int(v, lo, hi, field):
    if isinstance(v, bool) or not isinstance(v, int) or not lo <= v <= hi:
        raise ApiError(400, f"{field} must be an integer {lo}..{hi}")
    return v


def capabilities():
    pil = export_manager.has_pillow()
    return {"pillow": pil, "formats": list(FORMATS) if pil else ["png"]}


def _cleanup():
    root = config.EXPORTS_DIR
    if not root.exists():
        return
    cutoff = time.time() - config.EXPORT_TTL_HOURS * 3600
    for d in root.iterdir():
        job = d / "job.json"
        if d.is_dir() and job.exists() and job.stat().st_mtime < cutoff:
            shutil.rmtree(d, ignore_errors=True)


def create_job(data):
    if not isinstance(data, dict):
        raise ApiError(400, "Body must be a JSON object")
    pid = data.get("project_id")
    if not isinstance(pid, str) or not repo.exists(pid):
        raise ApiError(404, "Project not found")
    fmt = data.get("format")
    if fmt not in FORMATS:
        raise ApiError(400, "format must be one of: " + ", ".join(FORMATS))
    if fmt != "png" and not export_manager.has_pillow():
        raise ApiError(501, "GIF and sprite sheet export need Pillow. Install it with: pip install pillow")
    n = _int(data.get("frames"), 1, config.MAX_EXPORT_FRAMES, "frames")
    fps = data.get("fps", 12)
    if isinstance(fps, bool) or not isinstance(fps, (int, float)) or not 0 < fps <= 120:
        raise ApiError(400, "fps must be a number in (0, 120]")
    job = {
        "id": uuid.uuid4().hex[:12], "project_id": pid, "format": fmt, "frames": n, "fps": fps,
        "transparent": bool(data.get("transparent", False)), "loop": bool(data.get("loop", True)),
        "columns": _int(data.get("columns", 0), 0, 1000, "columns"),
        "padding": _int(data.get("padding", 0), 0, 64, "padding"),
        "base": _slug(data.get("name")), "created": int(time.time()),
    }
    _cleanup()
    d = _dir(job["id"])
    (d / "frames").mkdir(parents=True, exist_ok=True)
    write_json_atomic(d / "job.json", job, backup=False)
    return {"job_id": job["id"], "frames": n}


def save_frame(job_id, index, data):
    job = _load(job_id)
    if not 0 <= index < job["frames"]:
        raise ApiError(400, f"frame index must be 0..{job['frames'] - 1}")
    if not data.startswith(PNG_MAGIC):
        raise ApiError(400, "Frame must be a PNG image")
    (_dir(job_id) / "frames" / f"{index:05d}.png").write_bytes(data)


def finish(job_id):
    job = _load(job_id)
    d = _dir(job_id)
    out = job.get("output")
    if not out or not (d / out).exists():
        paths = [d / "frames" / f"{i:05d}.png" for i in range(job["frames"])]
        missing = [i for i, p in enumerate(paths) if not p.exists()]
        if missing:
            raise ApiError(422, f"{len(missing)} frame(s) were not uploaded", [f"frame {i}" for i in missing[:5]])
        try:
            out = export_manager.build(paths, d, job)
        except ValueError as e:
            raise ApiError(422, str(e))
        shutil.rmtree(d / "frames", ignore_errors=True)
        job["output"] = out
        write_json_atomic(d / "job.json", job, backup=False)
    return {"job_id": job_id, "filename": out, "size": (d / out).stat().st_size, "url": f"/api/exports/{job_id}/download"}


def output_file(job_id):
    job = _load(job_id)
    out = job.get("output")
    path = _dir(job_id) / out if out else None
    if not path or not path.exists():
        raise ApiError(404, "Export is not ready yet")
    return path, out
