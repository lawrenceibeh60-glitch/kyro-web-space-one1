"""backend/services/project_service.py - project CRUD rules."""
import json
import re
import uuid
from datetime import datetime, timezone

import config
from backend.app.exceptions import ApiError
from backend.services.validation_service import validate_project
from backend.storage import project_repository as repo

DEFAULT_SETTINGS = {"width": 1280, "height": 720, "fps": 12, "duration_frames": 24, "background": "#ffffff"}
DEMO_TEMPLATES = {
    "bounce": ("Bouncing Ball", "#f3efe6", 24),
    "parallax": ("Parallax Ridge", "#d7eff2", 48),
    "pendulum": ("Pendulum Study", "#f2eadb", 48),
    "orbit": ("Orbit Study", "#121b35", 48),
}


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _new_id(name):
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")[:40] or "project"
    return f"{slug}_{uuid.uuid4().hex[:6]}"


def create_project(name, settings=None):
    if not isinstance(name, str) or not name.strip():
        raise ApiError(400, "name must be a non-empty string")
    s = dict(DEFAULT_SETTINGS)
    if isinstance(settings, dict):
        s.update({k: v for k, v in settings.items() if k in DEFAULT_SETTINGS})
    now = _now()
    project = {
        "format": "kae",
        "version": config.FORMAT_VERSION,
        "id": _new_id(name),
        "name": name.strip(),
        "created": now,
        "modified": now,
        "settings": s,
        "palette": ["#111111", "#e63946", "#457b9d", "#f1faee"],
        "drawings": {},
        "characters": [],
        "effects": [],
        "rigs": [],
        "audio": [],
        "scenes": [{
            "id": "scene_1", "name": "Scene 1",
            "camera": {"transform": {"x": 0, "y": 0, "scale_x": 1, "scale_y": 1}, "tracks": {}},
            "layers": [{"id": "layer_1", "name": "Layer 1", "type": "drawing", "exposures": []}],
        }],
    }
    errs = validate_project(project)
    if errs:
        raise ApiError(422, "Invalid project settings", errs)
    repo.save(project["id"], project)
    return project


def _circle(cx, cy, radius, count=20):
    import math

    return [[round(cx + math.cos(i * math.tau / count) * radius, 2),
             round(cy + math.sin(i * math.tau / count) * radius, 2), 1]
            for i in range(count)]


def _shape(stroke_id, points, color, width=3, fill=None, closed=False):
    stroke = {"id": stroke_id, "tool": "brush", "color": color, "width": width, "points": points}
    if fill is not None:
        stroke["fill"] = fill
    if closed:
        stroke["closed"] = True
    return stroke


def _layer(layer_id, name, drawing_id, depth=1, transform=None, tracks=None):
    layer = {
        "id": layer_id, "name": name, "type": "drawing", "depth": depth,
        "exposures": [{"start": 0, "length": 48, "drawing": drawing_id}],
    }
    if transform:
        layer["transform"] = transform
    if tracks:
        layer["tracks"] = tracks
    return layer


def _create_studio_demo(template):
    name, background, duration = DEMO_TEMPLATES[template]
    if template == "bounce":
        src = config.BASE_DIR / "formats" / "examples" / "project.json"
        if not src.exists():
            raise ApiError(404, "Demo project file is missing")
        with open(src, "r", encoding="utf-8") as f:
            project = json.load(f)
        now = _now()
        project.update({
            "id": _new_id(name), "name": "Bouncing Ball (demo)",
            "created": now, "modified": now,
        })
        project["scenes"][0]["layers"][0]["depth"] = 0.3
        project["scenes"][0]["layers"][1]["depth"] = 1.2
        project["scenes"][0]["lights"] = [{
            "id": "light_sun", "x": 930, "y": 178, "radius": 520,
            "intensity": 0.3, "color": "#fff0b3",
        }]
        errs = validate_project(project)
        if errs:
            raise ApiError(422, f"{name} demo failed validation", errs)
        repo.save(project["id"], project)
        return project

    now = _now()
    project = {
        "format": "kae", "version": config.FORMAT_VERSION,
        "id": _new_id(name), "name": name, "created": now, "modified": now,
        "settings": {**DEFAULT_SETTINGS, "width": 1280, "height": 720,
                     "fps": 24, "duration_frames": duration, "background": background},
        "palette": [], "drawings": {}, "characters": [], "scenes": [],
        "effects": [], "rigs": [], "audio": [],
    }
    drawings = project["drawings"]
    layers = []

    if template == "parallax":
        drawings.update({
            "d_sky": {"id": "d_sky", "name": "Distant haze", "strokes": [
                _shape("sun", _circle(930, 178, 68), "#fff4bd", 2, "#fff4bd", True),
                _shape("cloud", [[180, 198], [218, 172], [260, 194], [296, 178], [330, 202]], "#ffffff", 15),
            ]},
            "d_peaks_far": {"id": "d_peaks_far", "name": "Far peaks", "strokes": [
                _shape("peaks", [[0, 490], [195, 260], [340, 416], [560, 210], [795, 455],
                                 [1000, 270], [1280, 500], [1280, 720], [0, 720]],
                       "#98b9bf", 2, "#98b9bf", True),
            ]},
            "d_peaks_near": {"id": "d_peaks_near", "name": "Near ridge", "strokes": [
                _shape("ridge", [[0, 540], [230, 410], [410, 520], [650, 340], [860, 518],
                                 [1050, 390], [1280, 520], [1280, 720], [0, 720]],
                       "#497e76", 2, "#497e76", True),
            ]},
            "d_foreground": {"id": "d_foreground", "name": "Foreground grass", "strokes": [
                _shape("ground", [[0, 630], [260, 590], [500, 642], [820, 570],
                                  [1020, 625], [1280, 570], [1280, 720], [0, 720]],
                       "#294f4d", 2, "#294f4d", True),
            ]},
        })
        layers = [
            _layer("layer_sky", "Distant sky", "d_sky", 0.08,
                   tracks={"x": [{"t": 0, "v": -18}, {"t": 47, "v": 18}]}),
            _layer("layer_far", "Far mountains", "d_peaks_far", 0.3,
                   tracks={"x": [{"t": 0, "v": 15}, {"t": 47, "v": -15}]}),
            _layer("layer_near", "Near ridge", "d_peaks_near", 0.72,
                   tracks={"x": [{"t": 0, "v": -28}, {"t": 47, "v": 28}]}),
            _layer("layer_front", "Foreground", "d_foreground", 1.35,
                   tracks={"x": [{"t": 0, "v": 45}, {"t": 47, "v": -45}]}),
        ]
        camera_tracks = {
            "x": [{"t": 0, "v": -100, "ease": "ease_in_out"}, {"t": 47, "v": 100}],
            "scale_x": [{"t": 0, "v": 1}, {"t": 47, "v": 1.12, "ease": "ease_in_out"}],
        }
    elif template == "pendulum":
        drawings["d_pendulum"] = {"id": "d_pendulum", "name": "Pendulum", "strokes": [
            _shape("cord", [[640, 115], [640, 435]], "#594936", 8),
            _shape("bob-rim", _circle(640, 510, 74), "#48372d", 8, "#b96e45", True),
            _shape("bob-shine", _circle(616, 486, 18), "#f5cc91", 4, "#f5cc91", True),
            _shape("pivot", _circle(640, 115, 20), "#48372d", 4, "#d8b77c", True),
        ]}
        drawings["d_guides"] = {"id": "d_guides", "name": "Swing guides", "strokes": [
            _shape("arc", [[365, 235], [420, 195], [485, 164], [560, 135], [640, 125],
                           [720, 135], [795, 164], [860, 195], [915, 235]], "#cfb98e", 3),
            _shape("base", [[530, 96], [750, 96]], "#75644c", 8),
        ]}
        layers = [
            _layer("layer_guides", "Swing guides", "d_guides", 0.25),
            _layer("layer_pendulum", "Pendulum", "d_pendulum", 1, {"x": 640, "y": 115, "anchor_x": 640, "anchor_y": 115},
                   {"rotation": [{"t": 0, "v": -32, "ease": "ease_in_out"},
                                 {"t": 24, "v": 32, "ease": "ease_in_out"},
                                 {"t": 47, "v": -32}]})
        ]
        camera_tracks = {}
    else:
        drawings["d_orbit"] = {"id": "d_orbit", "name": "Orbit", "strokes": [
            _shape("orbit-outer", _circle(640, 360, 230), "#50658e", 3),
            _shape("orbit-inner", _circle(640, 360, 145), "#3b4e72", 2),
            _shape("star", _circle(640, 360, 54), "#ffe3a6", 3, "#f5b94e", True),
            _shape("shine", _circle(624, 341, 13), "#fff5d6", 2, "#fff5d6", True),
        ]}
        drawings["d_planet"] = {"id": "d_planet", "name": "Orbiting planet", "strokes": [
            _shape("planet", _circle(0, 0, 27), "#bbd5ff", 4, "#6ca9d2", True),
            _shape("crater", _circle(8, -8, 6), "#487ba3", 2, "#487ba3", True),
        ]}
        drawings["d_moon"] = {"id": "d_moon", "name": "Tiny moon", "strokes": [
            _shape("moon", _circle(0, 0, 12), "#d8c9ff", 2, "#a78ce2", True),
        ]}
        layers = [
            _layer("layer_orbits", "Orbit paths", "d_orbit", 0.25),
            _layer("layer_moon", "Moon", "d_moon", 0.65, tracks={
                "x": [{"t": 0, "v": 785}, {"t": 12, "v": 640}, {"t": 24, "v": 495},
                      {"t": 36, "v": 640}, {"t": 47, "v": 785}],
                "y": [{"t": 0, "v": 360}, {"t": 12, "v": 215}, {"t": 24, "v": 360},
                      {"t": 36, "v": 505}, {"t": 47, "v": 360}],
            }),
            _layer("layer_planet", "Planet", "d_planet", 1.2,
                   tracks={
                       "x": [{"t": 0, "v": 870}, {"t": 12, "v": 640}, {"t": 24, "v": 410},
                             {"t": 36, "v": 640}, {"t": 47, "v": 870}],
                       "y": [{"t": 0, "v": 360}, {"t": 12, "v": 130}, {"t": 24, "v": 360},
                             {"t": 36, "v": 590}, {"t": 47, "v": 360}],
                   }),
        ]
        camera_tracks = {}

    project["drawings"] = drawings
    project["scenes"] = [{
        "id": "scene_1", "name": name,
        "camera": {
            "transform": {"x": 0, "y": 0, "scale_x": 1},
            "tracks": camera_tracks,
        },
        "lights": [],
        "layers": layers,
    }]
    if template == "parallax":
        project["scenes"][0]["lights"] = [{
            "id": "light_sun", "x": 930, "y": 178, "radius": 520,
            "intensity": 0.3, "color": "#fff0b3",
        }]
    now = _now()
    project.update({"id": _new_id(name), "created": now, "modified": now})
    errs = validate_project(project)
    if errs:
        raise ApiError(422, f"{name} demo failed validation", errs)
    repo.save(project["id"], project)
    return project


def create_demo(template="bounce"):
    if template not in DEMO_TEMPLATES:
        raise ApiError(404, f"Unknown demo '{template}'")
    return _create_studio_demo(template)


def get_project(pid):
    return repo.load(pid)


def save_project(pid, data):
    if data.get("id") != pid:
        raise ApiError(400, "Document id does not match URL id")
    _check_supported_version(data)
    errs = validate_project(data)
    if errs:
        raise ApiError(422, "Project failed validation", errs)
    if not repo.exists(pid):
        raise ApiError(404, f"Project '{pid}' not found")
    data["modified"] = _now()
    repo.save(pid, data)
    return data


def list_projects():
    out = []
    for pid in repo.list_ids():
        try:
            p = repo.load(pid)
            out.append({"id": pid, "name": p.get("name", pid), "modified": p.get("modified", "")})
        except Exception:
            out.append({"id": pid, "name": pid, "modified": "", "corrupt": True})
    out.sort(key=lambda x: x["modified"], reverse=True)
    return out


def delete_project(pid):
    repo.delete(pid)


def _check_supported_version(data):
    version = data.get("version")
    if isinstance(version, int) and not isinstance(version, bool) and version > config.FORMAT_VERSION:
        raise ApiError(
            422,
            f"Project version {version} is newer than the supported version {config.FORMAT_VERSION}",
        )


def import_project(data):
    if not isinstance(data, dict):
        raise ApiError(400, "Import payload must be a JSON object")
    data = dict(data)
    if "id" not in data:
        name = data.get("name")
        data["id"] = _new_id(name if isinstance(name, str) and name.strip() else "imported")
    if "format" not in data:
        data["format"] = "kae"
    if "version" not in data:
        data["version"] = config.FORMAT_VERSION
    _check_supported_version(data)
    if "settings" not in data:
        data["settings"] = dict(DEFAULT_SETTINGS)
    elif isinstance(data["settings"], dict):
        data["settings"] = {**DEFAULT_SETTINGS, **data["settings"]}
    if "scenes" not in data:
        data["scenes"] = [{
            "id": "scene_1",
            "name": "Scene 1",
            "camera": {
                "transform": {"x": 0, "y": 0, "scale_x": 1, "scale_y": 1},
                "tracks": {},
            },
            "layers": [{
                "id": "layer_1",
                "name": "Layer 1",
                "type": "drawing",
                "exposures": [],
            }],
        }]
    if "drawings" not in data:
        data["drawings"] = {}
    for field in ("palette", "characters", "effects", "rigs", "audio"):
        data.setdefault(field, [])
    errs = validate_project(data)
    if errs:
        raise ApiError(422, "Imported project failed validation", errs)
    pid = data["id"]
    data["modified"] = _now()
    repo.save(pid, data)
    return data
