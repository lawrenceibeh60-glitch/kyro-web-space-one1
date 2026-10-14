"""backend/services/project_service.py - project CRUD rules."""
import json
import re
import uuid
from datetime import datetime, timezone

import config
from backend.app.exceptions import ApiError
from backend.services.validation_service import validate_project
from backend.storage import project_repository as repo
from engine.core.errors import ValidationError
from engine.project.project_migration import migrate_project

DEFAULT_SETTINGS = {"width": 1280, "height": 720, "fps": 12, "duration_frames": 24, "background": "#ffffff"}
DEMO_TEMPLATES = {
    "bounce": ("Bouncing Ball", "#f3efe6", 24),
    "parallax": ("Parallax Ridge", "#d7eff2", 48),
    "pendulum": ("Pendulum Study", "#f2eadb", 48),
    "orbit": ("Orbit Study", "#121b35", 48),
    "cinematic": ("Cinematic Camera Move", "#111722", 200),
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
        "styles": [],
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
        project = migrate_project(project)
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
        "palette": [], "styles": [], "drawings": {}, "characters": [], "scenes": [],
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
    elif template == "cinematic":
        # A fully editable 200-frame camera choreography study (24 fps).
        # Camera tracks use real KAE interpolation; no runtime-only animation tricks.
        drawings.update({
            "d_skyline": {"id": "d_skyline", "name": "Distant skyline", "strokes": [
                _shape("skyline", [[0, 350], [70, 350], [70, 260], [125, 260], [125, 315],
                    [195, 315], [195, 205], [250, 205], [250, 330], [320, 330],
                    [320, 240], [385, 240], [385, 295], [455, 295], [455, 180],
                    [520, 180], [520, 320], [600, 320], [600, 220], [670, 220],
                    [670, 290], [740, 290], [740, 170], [810, 170], [810, 320],
                    [900, 320], [900, 235], [970, 235], [970, 300], [1040, 300],
                    [1040, 195], [1110, 195], [1110, 330], [1180, 330],
                    [1180, 250], [1280, 250], [1280, 720], [0, 720]],
                    "#202c3b", 2, "#202c3b", True),
            ]},
            "d_ground": {"id": "d_ground", "name": "Wet street", "strokes": [
                _shape("road", [[0, 520], [1280, 520], [1280, 720], [0, 720]],
                    "#18212c", 2, "#18212c", True),
                _shape("reflection_a", [[160, 575], [360, 575]], "#526a80", 5),
                _shape("reflection_b", [[780, 620], [1090, 620]], "#354a5e", 4),
                _shape("reflection_c", [[430, 675], [610, 675]], "#526a80", 3),
                _shape("horizon", [[0, 520], [1280, 520]], "#72869a", 2),
            ]},
            "d_character_front": {"id": "d_character_front", "name": "Walker front pose", "strokes": [
                _shape("coat", [[584, 325], [696, 325], [722, 475], [688, 490],
                    [700, 555], [580, 555], [592, 490], [558, 475]],
                    "#d8e0e9", 5, "#d8e0e9", True),
                _shape("neck", [[615, 292], [665, 292], [665, 337], [615, 337]],
                    "#b8c6d5", 3, "#b8c6d5", True),
                _shape("head", _circle(640, 250, 58, 24), "#e4c9b5", 5, "#e4c9b5", True),
                _shape("hair", [[582, 252], [584, 218], [601, 190], [637, 180],
                    [674, 191], [696, 222], [691, 254], [672, 224], [645, 210],
                    [615, 226], [596, 254]], "#20202b", 4, "#20202b", True),
                _shape("eye_l", [[615, 251], [629, 251]], "#20202b", 4),
                _shape("eye_r", [[651, 251], [665, 251]], "#20202b", 4),
                _shape("arm_l", [[576, 352], [541, 425], [558, 450]], "#c7d2df", 16),
                _shape("arm_r", [[704, 352], [738, 405], [718, 438]], "#c7d2df", 16),
                _shape("leg_l", [[608, 548], [592, 638], [565, 677]], "#7f9bb4", 25),
                _shape("leg_r", [[670, 548], [690, 620], [722, 657]], "#a7bbcd", 25),
                _shape("shoe_l", [[565, 677], [535, 686], [590, 692]], "#d9e1ea", 8),
                _shape("shoe_r", [[722, 657], [745, 671], [700, 675]], "#d9e1ea", 8),
            ]},
            "d_character_profile": {"id": "d_character_profile", "name": "Walker profile pose", "strokes": [
                _shape("coat", [[625, 325], [690, 340], [700, 470], [680, 550],
                    [590, 550], [610, 465]], "#d8e0e9", 5, "#d8e0e9", True),
                _shape("neck", [[625, 290], [660, 300], [654, 337], [622, 333]],
                    "#b8c6d5", 3, "#b8c6d5", True),
                _shape("head", _circle(640, 250, 56, 24), "#e4c9b5", 5, "#e4c9b5", True),
                _shape("hair", [[584, 250], [585, 215], [608, 190], [646, 183],
                    [679, 202], [695, 235], [681, 261], [666, 226], [636, 210],
                    [607, 228]], "#20202b", 4, "#20202b", True),
                _shape("profile_eye", [[665, 247], [674, 250]], "#20202b", 4),
                _shape("profile_nose", [[686, 253], [700, 263], [686, 267]], "#b78f7d", 3),
                _shape("arm", [[632, 355], [605, 420], [628, 450]], "#c7d2df", 16),
                _shape("leg_back", [[620, 545], [580, 610], [590, 666]], "#7f9bb4", 23),
                _shape("leg_front", [[662, 545], [700, 604], [670, 665]], "#a7bbcd", 25),
                _shape("shoe_back", [[590, 666], [564, 678], [610, 681]], "#d9e1ea", 8),
                _shape("shoe_front", [[670, 665], [700, 677], [652, 682]], "#d9e1ea", 8),
            ]},
        })

        # Convert the hand-drawn front/profile art into independent character-part
        # drawings so the real rig/clip renderer animates limbs instead of a single
        # flattened illustration.
        front_source = {stroke["id"]: stroke for stroke in drawings["d_character_front"]["strokes"]}
        profile_source = {stroke["id"]: stroke for stroke in drawings["d_character_profile"]["strokes"]}
        # Split the original leg strokes at the knee so the two-bone IK solver can
        # preserve planted feet while the upper and lower legs articulate separately.
        front_source.update({
            "left_thigh": _shape("left_thigh", [[608, 548], [592, 612]], "#7f9bb4", 25),
            "left_shin": _shape("left_shin", [[592, 612], [565, 677]], "#7f9bb4", 25),
            "right_thigh": _shape("right_thigh", [[670, 548], [690, 604]], "#a7bbcd", 25),
            "right_shin": _shape("right_shin", [[690, 604], [722, 657]], "#a7bbcd", 25),
        })
        profile_source.update({
            "left_thigh": _shape("left_thigh_profile", [[620, 545], [580, 610]], "#7f9bb4", 23),
            "left_shin": _shape("left_shin_profile", [[580, 610], [590, 666]], "#7f9bb4", 23),
            "right_thigh": _shape("right_thigh_profile", [[662, 545], [700, 604]], "#a7bbcd", 25),
            "right_shin": _shape("right_shin_profile", [[700, 604], [670, 665]], "#a7bbcd", 25),
        })
        # Back-to-front painter order: legs and arms behind the coat, then head and shoes.
        part_specs = [
            ("left_thigh", "Left thigh", ["left_thigh"], ["left_thigh"], (608, 548), "torso"),
            ("left_shin", "Left shin", ["left_shin"], ["left_shin"], (592, 612), "left_thigh"),
            ("right_thigh", "Right thigh", ["right_thigh"], ["right_thigh"], (670, 548), "torso"),
            ("right_shin", "Right shin", ["right_shin"], ["right_shin"], (690, 604), "right_thigh"),
            ("left_upper_arm", "Left arm", ["arm_l"], ["arm"], (575, 352), "torso"),
            ("right_upper_arm", "Right arm", ["arm_r"], [], (705, 352), "torso"),
            ("torso", "Torso", ["coat", "neck"], ["coat", "neck"], (640, 420), None),
            ("head", "Head", ["head", "hair", "eye_l", "eye_r"],
             ["head", "hair", "profile_eye", "profile_nose"], (640, 250), "torso"),
            ("left_foot", "Left shoe", ["shoe_l"], ["shoe_back"], (565, 677), "left_shin"),
            ("right_foot", "Right shoe", ["shoe_r"], ["shoe_front"], (722, 657), "right_shin"),
        ]
        walker_parts = []
        walker_bones = []
        walker_layers = []
        motion_tracks = {
            "x": [
                {"t": 0, "v": 0, "ease": "ease_in_out"},
                {"t": 49, "v": 0, "ease": "ease_in_out"},
                {"t": 99, "v": -20, "ease": "ease_in_out"},
                {"t": 149, "v": -30, "ease": "ease_in_out"},
                {"t": 199, "v": -30},
            ],
            "y": [
                {"t": 0, "v": 8, "ease": "ease_in_out"},
                {"t": 49, "v": 0, "ease": "ease_in_out"},
                {"t": 99, "v": 5, "ease": "ease_in_out"},
                {"t": 149, "v": 0, "ease": "ease_in_out"},
                {"t": 199, "v": 0},
            ],
        }
        for part_id, part_name, front_ids, profile_ids, pivot, parent_id in part_specs:
            front_strokes = [front_source[key] for key in front_ids]
            profile_strokes = [profile_source[key] for key in profile_ids]
            front_drawing = f"d_front_{part_id}"
            profile_drawing = f"d_profile_{part_id}"
            drawings[front_drawing] = {
                "id": front_drawing, "name": f"Walker {part_name} (front)",
                "strokes": front_strokes,
            }
            drawings[profile_drawing] = {
                "id": profile_drawing, "name": f"Walker {part_name} (profile)",
                "strokes": profile_strokes,
            }
            walker_parts.append({"id": part_id, "name": part_name, "strokes": front_strokes})
            bone = {
                "id": part_id, "name": part_name, "character_part_id": part_id,
                "pivot": {"x": pivot[0], "y": pivot[1]},
            }
            if parent_id:
                bone["parent_id"] = parent_id
            walker_bones.append(bone)
            common = {
                "type": "drawing", "depth": 1.15, "character_id": "character_walker",
                "character_part_id": part_id, "transform": {"x": 0, "y": 0},
                "tracks": motion_tracks,
            }
            walker_layers.extend([
                {
                    **common, "id": f"layer_walker_{part_id}_front",
                    "name": f"Walker / {part_name} (front)",
                    "exposures": [{"start": 0, "length": 104, "drawing": front_drawing}],
                    "tracks": {
                        **motion_tracks,
                        "rotation_y": [
                            {"t": 0, "v": 0},
                            {"t": 95, "v": 0, "ease": "ease_in_out"},
                            {"t": 100, "v": 90, "ease": "ease_in_out"},
                            {"t": 103, "v": 90},
                            {"t": 199, "v": 90},
                        ],
                        "opacity": [
                            {"t": 0, "v": 1}, {"t": 95, "v": 1},
                            {"t": 100, "v": 0.5, "ease": "ease_in_out"},
                            {"t": 103, "v": 0}, {"t": 199, "v": 0},
                        ],
                    },
                },
                {
                    **common, "id": f"layer_walker_{part_id}_profile",
                    "name": f"Walker / {part_name} (profile)",
                    "exposures": [{"start": 96, "length": 104, "drawing": profile_drawing}],
                    "tracks": {
                        **motion_tracks,
                        "opacity": [
                            {"t": 0, "v": 0}, {"t": 96, "v": 0},
                            {"t": 100, "v": 0.5, "ease": "ease_in_out"},
                            {"t": 104, "v": 1}, {"t": 199, "v": 1},
                        ],
                    },
                },
            ])
        drawings.pop("d_character_front")
        drawings.pop("d_character_profile")
        project["characters"] = [{
            "format": "kae-character", "version": 1, "id": "character_walker",
            "name": "Cinematic Walker", "parts": walker_parts,
        }]
        project["rigs"] = [{
            "id": "rig_walker", "name": "Cinematic Walker Rig",
            "character_id": "character_walker",
            "animation": {
                "type": "walk", "enabled": True, "start_frame": 0,
                "cycle_frames": 24, "speed": 1, "stride": 28,
                "bob": 5, "weight": 1, "loop": True,
            },
            "bones": walker_bones,
        }]
        layers = [
            _layer("layer_skyline", "Distant skyline", "d_skyline", 0.22,
                tracks={"x": [{"t": 0, "v": -8}, {"t": 199, "v": 8, "ease": "ease_in_out"}]}),
            _layer("layer_ground", "Wet street", "d_ground", 0.72,
                tracks={"x": [{"t": 0, "v": 20}, {"t": 199, "v": -20, "ease": "ease_in_out"}]}),
            *walker_layers,
        ]
        for layer in layers:
            if layer.get("character_id") == "character_walker":
                continue
            for exposure in layer.get("exposures", []):
                exposure["length"] = duration
        camera_tracks = {
            "x": [
                {"t": 0, "v": 0, "ease": "ease_in_out"},
                {"t": 39, "v": 0, "ease": "ease_in_out"},
                {"t": 49, "v": 0, "ease": "ease_in_out"},
                {"t": 99, "v": 36, "ease": "ease_in_out"},
                {"t": 119, "v": 56, "ease": "ease_in_out"},
                {"t": 179, "v": 95, "ease": "ease_in_out"},
                {"t": 199, "v": 95},
            ],
            "y": [
                {"t": 0, "v": 75, "ease": "ease_in_out"},
                {"t": 39, "v": 75, "ease": "ease_in_out"},
                {"t": 49, "v": 0, "ease": "ease_in_out"},
                {"t": 99, "v": 0, "ease": "ease_in_out"},
                {"t": 119, "v": -8, "ease": "ease_in_out"},
                {"t": 179, "v": -8, "ease": "ease_in_out"},
                {"t": 199, "v": -8},
            ],
            "rotation": [
                {"t": 0, "v": -1.5, "ease": "ease_in_out"},
                {"t": 39, "v": -1.5, "ease": "ease_in_out"},
                {"t": 49, "v": 0, "ease": "ease_in_out"},
                {"t": 99, "v": 0, "ease": "ease_in_out"},
                {"t": 119, "v": 1.2, "ease": "ease_in_out"},
                {"t": 179, "v": 0.2, "ease": "ease_in_out"},
                {"t": 199, "v": 0},
            ],
            "scale_x": [
                {"t": 0, "v": 2.25, "ease": "ease_in_out"},
                {"t": 39, "v": 2.25, "ease": "ease_in_out"},
                {"t": 49, "v": 1.0, "ease": "ease_in_out"},
                {"t": 99, "v": 1.08, "ease": "ease_in_out"},
                {"t": 119, "v": 1.16, "ease": "ease_in_out"},
                {"t": 179, "v": 1.12, "ease": "ease_in_out"},
                {"t": 199, "v": 1.08},
            ],
            "scale_y": [
                {"t": 0, "v": 2.05, "ease": "ease_in_out"},
                {"t": 39, "v": 2.05, "ease": "ease_in_out"},
                {"t": 49, "v": 1.0, "ease": "ease_in_out"},
                {"t": 99, "v": 1.04, "ease": "ease_in_out"},
                {"t": 119, "v": 1.12, "ease": "ease_in_out"},
                {"t": 179, "v": 1.08, "ease": "ease_in_out"},
                {"t": 199, "v": 1.04},
            ],
        }
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
            "transform": {"x": 0, "y": 0, "scale_x": 1, "scale_y": 1},
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
    project = repo.load(pid)
    errors = validate_project(project)
    if errors:
        raise ApiError(422, "Project failed validation", errors)
    return _migrate_project(project)


def save_project(pid, data):
    if data.get("id") != pid:
        raise ApiError(400, "Document id does not match URL id")
    _check_supported_version(data)
    errors = validate_project(data)
    if errors:
        raise ApiError(422, "Project failed validation", errors)
    data = _migrate_project(data)
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


def _migrate_project(data):
    try:
        return migrate_project(data)
    except ValidationError as error:
        raise ApiError(422, str(error)) from error


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
        data["version"] = 1
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
    data = _migrate_project(data)
    errs = validate_project(data)
    if errs:
        raise ApiError(422, "Imported project failed validation", errs)
    pid = data["id"]
    data["modified"] = _now()
    repo.save(pid, data)
    return data
