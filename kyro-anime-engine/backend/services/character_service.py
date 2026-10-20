"""Character registry and stable, editable character-part imports."""
from copy import deepcopy
import math
import re

from backend.app.exceptions import ApiError
from backend.services.validation_service import validate_character_document, validate_project
from backend.storage import project_repository as repo


def _project(pid):
    return repo.load(pid)


def list_characters(pid):
    return _project(pid).get("characters", [])


def create_character(pid, payload):
    project = _project(pid)
    characters = project.setdefault("characters", [])
    data = payload or {}
    if not isinstance(data, dict):
        raise ApiError(400, "Character payload must be an object")
    character_id = data.get("id") or f"char_{len(characters) + 1}"
    character = next((item for item in characters if item.get("id") == character_id), None)
    if character is None:
        character = {"id": character_id, "name": data.get("name", "Untitled character")}
        characters.append(character)
    else:
        character["name"] = data.get("name", character.get("name", "Untitled character"))
    project["modified"] = project.get("modified", "")
    repo.save(pid, project)
    return character


def import_character(pid, payload):
    errors = validate_character_document(payload)
    if errors:
        raise ApiError(422, "Character JSON failed validation", errors)

    project = _project(pid)
    character_id = payload["id"]
    characters = project.setdefault("characters", [])
    old_character_index = next(
        (index for index, item in enumerate(characters)
         if isinstance(item, dict) and item.get("id") == character_id),
        -1,
    )
    old_character = characters[old_character_index] if old_character_index >= 0 else None
    old_parts = {
        part.get("id")
        for part in (old_character or {}).get("parts", [])
        if isinstance(part, dict)
    }
    old_layers = {}
    existing_character_scene = None
    for scene in project.get("scenes", []):
        for layer in scene.get("layers", []):
            if layer.get("character_id") != character_id:
                continue
            part_id = layer.get("character_part_id")
            if isinstance(part_id, str):
                old_layers[part_id] = deepcopy(layer)
                existing_character_scene = scene

    requested_scene_id = payload.get("scene_id")
    if requested_scene_id is not None:
        target_scene = next(
            (scene for scene in project["scenes"] if scene.get("id") == requested_scene_id),
            None,
        )
        if target_scene is None:
            raise ApiError(404, f"Scene '{requested_scene_id}' not found")
    else:
        target_scene = existing_character_scene or project["scenes"][0]

    parts = payload["parts"]
    generated_ids = {}
    for part in parts:
        part_id = part["id"]
        drawing_id = f"chdraw_{character_id}_{part_id}"
        layer_id = f"chlayer_{character_id}_{part_id}"
        if len(drawing_id) > 64 or len(layer_id) > 64:
            raise ApiError(
                422,
                "Character and part IDs are too long when combined",
                [f"part '{part_id}' produces an ID longer than 64 characters"],
            )
        generated_ids[part_id] = (drawing_id, layer_id)
        for scene in project["scenes"]:
            for layer in scene.get("layers", []):
                if (
                    layer.get("id") == layer_id
                    and not (
                        layer.get("character_id") == character_id
                        and layer.get("character_part_id") == part_id
                    )
                ):
                    raise ApiError(409, f"Layer ID '{layer_id}' is already in use")
        if drawing_id in project.get("drawings", {}) and not (
            old_character_index >= 0 and part_id in old_parts
        ):
            raise ApiError(409, f"Drawing ID '{drawing_id}' is already in use")

    for scene in project["scenes"]:
        scene["layers"] = [
            layer for layer in scene.get("layers", [])
            if layer.get("character_id") != character_id
        ]

    incoming_part_ids = {part["id"] for part in parts}
    for rig in project.get("rigs", []):
        if not isinstance(rig, dict) or rig.get("character_id") != character_id:
            continue
        bones = rig.get("bones", [])
        removed_bones = {
            bone.get("id"): bone.get("parent_id")
            for bone in bones
            if isinstance(bone, dict)
            and isinstance(bone.get("character_part_id"), str)
            and bone.get("character_part_id") not in incoming_part_ids
            and isinstance(bone.get("id"), str)
        }
        rig["bones"] = [
            deepcopy(bone) for bone in bones
            if isinstance(bone, dict)
            and isinstance(bone.get("character_part_id"), str)
            and bone.get("character_part_id") in incoming_part_ids
        ]
        for bone in rig["bones"]:
            parent_id = bone.get("parent_id")
            while isinstance(parent_id, str) and parent_id in removed_bones:
                parent_id = removed_bones[parent_id]
            bone["parent_id"] = parent_id
    for removed_part_id in old_parts - incoming_part_ids:
        stale_drawing_id = f"chdraw_{character_id}_{removed_part_id}"
        referenced = any(
            exposure.get("drawing") == stale_drawing_id
            for scene in project["scenes"]
            for layer in scene.get("layers", [])
            for exposure in layer.get("exposures", [])
        )
        if not referenced:
            project.get("drawings", {}).pop(stale_drawing_id, None)

    duration = project["settings"]["duration_frames"]
    for part in parts:
        part_id = part["id"]
        drawing_id, layer_id = generated_ids[part_id]
        project.setdefault("drawings", {})[drawing_id] = {
            "id": drawing_id,
            "name": f"{payload['name']} - {part['name']}",
            "strokes": deepcopy(part["strokes"]),
        }
        layer = old_layers.get(part_id, {
            "id": layer_id,
            "type": "drawing",
            "visible": True,
        })
        layer.update({
            "id": layer_id,
            "name": f"{payload['name']} - {part['name']}",
            "type": "drawing",
            "character_id": character_id,
            "character_part_id": part_id,
            "exposures": [{"start": 0, "length": duration, "drawing": drawing_id}],
        })
        if part_id not in old_layers or "transform" in part:
            if "transform" in part:
                layer["transform"] = deepcopy(part["transform"])
        if "tracks" in part:
            layer["tracks"] = deepcopy(part["tracks"])
        if "depth" in part:
            layer["depth"] = part["depth"]
        elif part_id not in old_layers:
            layer["depth"] = 1
        target_scene["layers"].append(layer)

    character = deepcopy(payload)
    character.pop("scene_id", None)
    if old_character_index >= 0:
        characters[old_character_index] = character
    else:
        characters.append(character)

    errors = validate_project(project)
    if errors:
        raise ApiError(422, "Imported character failed project validation", errors)
    project["modified"] = project.get("modified", "")
    repo.save(pid, project)
    return {"character": character, "project": project}


def _shape(stroke_id, points, color, fill=None, width=3):
    stroke = {
        "id": stroke_id, "tool": "brush", "color": color,
        "width": width, "points": points,
    }
    if fill is not None:
        stroke["fill"] = fill
        stroke["closed"] = True
    return stroke


def _oval(stroke_id, cx, cy, rx, ry, color, fill=None, width=3):
    points = [
        [round(cx + math.cos(index * math.tau / 24) * rx, 2),
         round(cy + math.sin(index * math.tau / 24) * ry, 2), 1]
        for index in range(24)
    ]
    return _shape(stroke_id, points, color, fill, width)


def build_head_strokes(cx, cy, sx, sy, skin, eyes, outline, expression):
    """Deterministic builder for head part strokes."""
    head = [
        _oval("head-outline", cx, cy, 142 * sx, 164 * sy, outline, skin, 6 * sx),
        _shape("ear-left", [[round(cx - 136 * sx, 2), round(cy + 10 * sy, 2), 1],
                            [round(cx - 160 * sx, 2), round(cy - 2 * sy, 2), 1],
                            [round(cx - 154 * sx, 2), round(cy + 42 * sy, 2), 1],
                            [round(cx - 132 * sx, 2), round(cy + 50 * sy, 2), 1]], outline, skin, 5 * sx),
        _shape("ear-right", [[round(cx + 136 * sx, 2), round(cy + 10 * sy, 2), 1],
                             [round(cx + 160 * sx, 2), round(cy - 2 * sy, 2), 1],
                             [round(cx + 154 * sx, 2), round(cy + 42 * sy, 2), 1],
                             [round(cx + 132 * sx, 2), round(cy + 50 * sy, 2), 1]], outline, skin, 5 * sx),
    ]
    for side, x in (("left", -55), ("right", 55)):
        head.extend([
            _oval(f"{side}-eye-white", cx + x * sx, cy + 20 * sy, 35 * sx, 43 * sy, outline, "#fff9f0", 4 * sx),
            _oval(f"{side}-iris", cx + x * sx, cy + 25 * sy, 20 * sx, 29 * sy, outline, eyes, 3 * sx),
            _oval(f"{side}-pupil", cx + x * sx, cy + 29 * sy, 9 * sx, 18 * sy, outline, "#171722", 2 * sx),
            _oval(f"{side}-glint", cx + (x - 6) * sx, cy + 14 * sy, 5 * sx, 7 * sy, "#ffffff", "#ffffff", 1 * sx),
        ])
    def pt(x, y):
        return [round(cx + x * sx, 2), round(cy + y * sy, 2), 1]
    head.extend([
        _shape("nose", [pt(0, 47), pt(-3, 57)], "#a86f68", None, 3 * sx),
        _shape("mouth",
               [pt(-20, 88), pt(-10, 94), pt(0, 96), pt(10, 94), pt(20, 88)]
               if expression == "smile" else [pt(-17, 92), pt(0, 92), pt(17, 92)],
               outline, None, 4 * sx),
        _shape("brow-left",
               [pt(-82, -42), pt(-55, -34), pt(-30, -30)]
               if expression == "determined" else [pt(-82, -31), pt(-55, -39), pt(-30, -31)],
               outline, None, 6 * sx),
        _shape("brow-right",
               [pt(30, -30), pt(55, -34), pt(82, -42)]
               if expression == "determined" else [pt(30, -31), pt(55, -39), pt(82, -31)],
               outline, None, 6 * sx),
    ])
    return head


def build_character_document(character_id, name, options, canvas_width, canvas_height):
    """Build a deterministic kae-character document from options without side effects.

    Returns a dict suitable for import_character or validate_character_document.
    Pure function: no project mutation, no I/O.
    """
    colors = {}
    for field, default in (
        ("hair_color", "#303b70"), ("eye_color", "#4c8ba8"),
        ("skin_color", "#f2c7a5"), ("outfit_color", "#a34f78"),
    ):
        value = options.get(field, default)
        if not isinstance(value, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
            raise ApiError(400, f"{field} must be a #RRGGBB color")
        colors[field] = value.lower()
    hairstyle = options.get("hairstyle", "short")
    if hairstyle not in {"short", "long", "twin_tails"}:
        raise ApiError(400, "hairstyle must be short, long, or twin_tails")
    expression = options.get("expression", "smile")
    if expression not in {"smile", "neutral", "determined"}:
        raise ApiError(400, "expression must be smile, neutral, or determined")

    scale = min(canvas_width / 500, canvas_height / 850, 1.0)
    cx, cy = canvas_width / 2, canvas_height * 0.23
    sx = sy = scale
    hair, eyes, skin, outfit = colors["hair_color"], colors["eye_color"], colors["skin_color"], colors["outfit_color"]
    outline = "#302b37"

    def pt(x, y):
        return [round(cx + x * sx, 2), round(cy + y * sy, 2), 1]
    def poly(stroke_id, coordinates, color, fill, stroke_width=4):
        return _shape(stroke_id, [pt(x, y) for x, y in coordinates], color, fill, stroke_width * sx)

    head = build_head_strokes(cx, cy, sx, sy, skin, eyes, outline, expression)
    hair_back = [
        poly("hair-crown", [(-148, 1), (-144, -86), (-102, -148), (-38, -177),
                            (35, -172), (111, -132), (150, -64), (147, 20),
                            (116, 2), (94, -56), (57, -87), (10, -103),
                            (-42, -91), (-91, -56), (-114, 5)], outline, hair, 7),
    ]
    hair_front = [
        poly("fringe", [(-135, -86), (-81, -125), (-48, -115), (-14, -63),
                        (17, -124), (48, -111), (72, -69), (117, -111),
                        (137, -72), (116, -14), (84, -43), (61, -3),
                        (31, -46), (0, -5), (-28, -49), (-63, -10),
                        (-88, -51), (-121, -28)], outline, hair, 6),
    ]
    parts = [
        {"id": "hair_back", "name": "Hair Back", "strokes": hair_back, "depth": 0.9},
        {"id": "left_thigh", "name": "Left Thigh", "strokes": [
            poly("left-thigh", [(-72, 354), (-8, 354), (-12, 455), (-82, 455)], outline, outfit, 7),
        ]},
        {"id": "left_shin", "name": "Left Shin", "strokes": [
            poly("left-shin", [(-82, 448), (-12, 448), (-18, 628), (-92, 628), (-84, 560)], outline, outfit, 7),
        ]},
        {"id": "left_foot", "name": "Left Foot", "strokes": [
            poly("left-shoe", [(-92, 619), (-20, 619), (-12, 652), (-111, 652)], outline, "#493d4b", 5),
        ]},
        {"id": "right_thigh", "name": "Right Thigh", "strokes": [
            poly("right-thigh", [(8, 354), (72, 354), (82, 455), (12, 455)], outline, outfit, 7),
        ]},
        {"id": "right_shin", "name": "Right Shin", "strokes": [
            poly("right-shin", [(12, 448), (82, 448), (84, 560), (92, 628), (18, 628)], outline, outfit, 7),
        ]},
        {"id": "right_foot", "name": "Right Foot", "strokes": [
            poly("right-shoe", [(20, 619), (92, 619), (111, 652), (12, 652)], outline, "#493d4b", 5),
        ]},
        {"id": "arm_left", "name": "Left Upper Arm", "strokes": [
            poly("left-upper-arm", [(-88, 192), (-126, 209), (-151, 266), (-124, 278), (-103, 247), (-83, 247)], outline, outfit, 7),
        ]},
        {"id": "forearm_left", "name": "Left Forearm", "strokes": [
            poly("left-forearm", [(-151, 266), (-124, 278), (-145, 344), (-174, 326)], outline, outfit, 7),
        ]},
        {"id": "hand_left", "name": "Left Hand", "strokes": [
            poly("left-hand", [(-174, 326), (-145, 344), (-134, 375), (-151, 385), (-171, 365), (-184, 344)], outline, skin, 5),
        ]},
        {"id": "arm_right", "name": "Right Upper Arm", "strokes": [
            poly("right-upper-arm", [(88, 192), (126, 209), (151, 266), (124, 278), (103, 247), (83, 247)], outline, outfit, 7),
        ]},
        {"id": "forearm_right", "name": "Right Forearm", "strokes": [
            poly("right-forearm", [(151, 266), (124, 278), (145, 344), (174, 326)], outline, outfit, 7),
        ]},
        {"id": "hand_right", "name": "Right Hand", "strokes": [
            poly("right-hand", [(174, 326), (145, 344), (134, 375), (151, 385), (171, 365), (184, 344)], outline, skin, 5),
        ]},
        {"id": "neck", "name": "Neck", "strokes": [
            poly("neck", [(-28, 138), (28, 138), (34, 178), (-34, 178)], outline, skin, 5),
        ]},
        {"id": "body", "name": "Outfit", "strokes": [
            poly("torso", [(-36, 164), (-102, 193), (-139, 310), (-106, 377), (106, 377), (139, 310), (102, 193), (36, 164)], outline, outfit, 8),
            poly("collar", [(-38, 169), (0, 204), (38, 169), (20, 237), (-20, 237)], outline, "#f5e8dd", 4),
        ]},
        {"id": "head", "name": "Face", "strokes": head},
        {"id": "hair_front", "name": "Hair Fringe", "strokes": hair_front},
    ]
    if hairstyle == "long":
        parts[0]["strokes"].extend([
            poly("left-lock", [(-119, -31), (-151, 17), (-145, 208), (-112, 277), (-96, 151)], outline, hair, 6),
            poly("right-lock", [(119, -31), (151, 17), (145, 208), (112, 277), (96, 151)], outline, hair, 6),
        ])
    elif hairstyle == "twin_tails":
        parts[0]["strokes"].extend([
            poly("left-tail", [(-105, -107), (-170, -125), (-204, -82), (-185, -9), (-217, 91), (-166, 117), (-134, 58), (-139, -12)], outline, hair, 6),
            poly("right-tail", [(105, -107), (170, -125), (204, -82), (185, -9), (217, 91), (166, 117), (134, 58), (139, -12)], outline, hair, 6),
        ])
    return {
        "format": "kae-character", "version": 1, "id": character_id,
        "name": name.strip(), "parts": parts,
    }


def generate_character(pid, options):
    """Build an editable anime-style vector character and import it by stable ID."""
    if not isinstance(options, dict):
        raise ApiError(400, "Generator options must be a JSON object")
    project = _project(pid)
    character_id = options.get("id")
    name = options.get("name")
    if not isinstance(character_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", character_id):
        raise ApiError(400, "A valid stable character id is required")
    if not isinstance(name, str) or not name.strip():
        raise ApiError(400, "Character name is required")
    doc = build_character_document(
        character_id, name, options,
        project["settings"]["width"], project["settings"]["height"],
    )
    return import_character(pid, doc)
