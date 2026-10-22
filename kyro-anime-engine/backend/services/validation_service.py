"""backend/services/validation_service.py
Dependency-free validation of a project document against formats/schemas
(structure + cross-references the JSON schemas can't express). Returns a list of error strings.
"""
import math
import re

from backend.services.schema_validator import validator as schema_validator

ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
CHANNELS = {
    "x", "y", "z", "rotation", "rotation_x", "rotation_y",
    "scale_x", "scale_y", "scale_z", "anchor_x", "anchor_y", "anchor_z",
    "opacity",
}
CAMERA_CHANNELS = {
    "x", "y", "z", "rotation", "rotation_x", "rotation_y",
    "scale_x", "scale_y", "fov", "focus_distance", "aperture",
}

EASES = {"linear", "hold", "ease_in", "ease_out", "ease_in_out"}
MAX_ERRORS = 50


def _num(v):
    return (
        isinstance(v, int) and not isinstance(v, bool)
        or isinstance(v, float) and math.isfinite(v)
    )


def _int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _check_settings(s, errs):
    if not isinstance(s, dict):
        errs.append("settings: must be an object")
        return
    for k in ("width", "height"):
        if not _int(s.get(k)) or not 16 <= s[k] <= 8192:
            errs.append(f"settings.{k}: integer 16..8192 required")
    if not _num(s.get("fps")) or not 0 < s["fps"] <= 120:
        errs.append("settings.fps: number in (0, 120] required")
    if not _int(s.get("duration_frames")) or s["duration_frames"] < 1:
        errs.append("settings.duration_frames: integer >= 1 required")


def _check_drawings(drawings, errs):
    if not isinstance(drawings, dict):
        errs.append("drawings: must be an object")
        return
    for key, d in drawings.items():
        w = f"drawings.{key}"
        if not isinstance(d, dict):
            errs.append(f"{w}: must be an object")
            continue
        if d.get("id") != key:
            errs.append(f"{w}: id must equal its key")
        strokes = d.get("strokes")
        if not isinstance(strokes, list):
            errs.append(f"{w}.strokes: must be a list")
            continue
        for i, s in enumerate(strokes):
            sw = f"{w}.strokes[{i}]"
            if not isinstance(s, dict):
                errs.append(f"{sw}: must be an object")
                continue
            if not isinstance(s.get("id"), str) or not ID_RE.match(s["id"]):
                errs.append(f"{sw}.id: invalid")
            _check_stroke(s, sw, errs)


def _check_tracks(tracks, where, errs, channels=CHANNELS):
    if not isinstance(tracks, dict):
        errs.append(f"{where}: tracks must be an object")
        return
    for ch, kfs in tracks.items():
        w = f"{where}.{ch}"
        if ch not in channels:
            errs.append(f"{w}: unknown channel")
            continue
        if not isinstance(kfs, list) or not kfs:
            errs.append(f"{w}: non-empty list required")
            continue
        last = -1
        for i, k in enumerate(kfs):
            kw = f"{w}[{i}]"
            if not isinstance(k, dict):
                errs.append(f"{kw}: must be an object")
                continue
            t = k.get("t")
            if not _int(t) or t < 0:
                errs.append(f"{kw}.t: integer >= 0 required")
            else:
                if t <= last:
                    errs.append(f"{kw}.t: keyframe times must strictly increase")
                last = t
            if not _num(k.get("v")):
                errs.append(f"{kw}.v: number required")
            e = k.get("ease", "linear")
            if isinstance(e, dict):
                b = e.get("bezier")
                ok = isinstance(b, list) and len(b) == 4 and all(_num(x) for x in b)
            else:
                ok = isinstance(e, str) and e in EASES
            if not ok:
                errs.append(f"{kw}.ease: invalid")


def _check_path_commands(commands, where, errs):
    if not isinstance(commands, list) or len(commands) < 2:
        errs.append(f"{where}: path requires a move and at least one segment")
        return
    expected_lengths = {"M": 3, "L": 3, "Q": 5, "C": 7, "Z": 1}
    has_segment = False
    has_current_point = False
    for index, command in enumerate(commands):
        path = f"{where}[{index}]"
        if (
            not isinstance(command, list)
            or not command
            or not isinstance(command[0], str)
            or command[0] not in expected_lengths
        ):
            errs.append(f"{path}: expected M, L, Q, C, or Z command")
            continue
        kind = command[0]
        if len(command) != expected_lengths[kind]:
            errs.append(f"{path}: {kind} command requires {expected_lengths[kind] - 1} coordinates")
            continue
        if not all(_num(value) for value in command[1:]):
            errs.append(f"{path}: coordinates must be finite numbers")
            continue
        if kind == "M":
            if index != 0:
                errs.append(f"{path}: only the first command may move to a new subpath")
            has_current_point = True
        elif kind == "Z":
            if not has_current_point:
                errs.append(f"{path}: close command requires a current point")
            has_segment = True
        elif has_current_point:
            has_segment = True
        else:
            errs.append(f"{path}: path must begin with a move command")
    if commands and (
        not isinstance(commands[0], list)
        or not commands[0]
        or commands[0][0] != "M"
    ):
        errs.append(f"{where}: path must begin with M")
    if not has_segment:
        errs.append(f"{where}: path requires at least one segment")


def _check_stroke(stroke, where, errs):
    points = stroke.get("points")
    commands = stroke.get("commands")
    if (points is None) == (commands is None):
        errs.append(f"{where}: exactly one of points or commands is required")
    if points is not None:
        if not isinstance(points, list) or not points:
            errs.append(f"{where}.points: non-empty list required")
        else:
            for index, point in enumerate(points):
                if not (
                    isinstance(point, list)
                    and 2 <= len(point) <= 3
                    and all(_num(value) for value in point)
                ):
                    errs.append(f"{where}.points[{index}]: expected [x, y, pressure?]")
                    break
    if commands is not None:
        _check_path_commands(commands, f"{where}.commands", errs)
    skin_weights = stroke.get("skin_weights")
    if skin_weights is not None:
        if points is None:
            errs.append(f"{where}.skin_weights: requires point-based geometry")
        elif not isinstance(skin_weights, list) or len(skin_weights) != len(points):
            errs.append(f"{where}.skin_weights: one influence list per point required")
        else:
            for point_index, influences in enumerate(skin_weights):
                sw = f"{where}.skin_weights[{point_index}]"
                if not isinstance(influences, list) or not influences:
                    errs.append(f"{sw}: non-empty influence list required")
                    continue
                total = 0.0
                seen_bones = set()
                for influence_index, influence in enumerate(influences):
                    iw = f"{sw}[{influence_index}]"
                    if not isinstance(influence, dict):
                        errs.append(f"{iw}: must be an object")
                        continue
                    if influence.keys() - {"bone_id", "weight"}:
                        errs.append(f"{iw}: unknown property")
                    bone_id = influence.get("bone_id")
                    if not isinstance(bone_id, str) or not ID_RE.fullmatch(bone_id):
                        errs.append(f"{iw}.bone_id: invalid")
                    elif bone_id in seen_bones:
                        errs.append(f"{iw}.bone_id: duplicate influence")
                    if isinstance(bone_id, str):
                        seen_bones.add(bone_id)
                    weight = influence.get("weight")
                    if not _num(weight) or not 0 <= weight <= 1:
                        errs.append(f"{iw}.weight: number 0..1 required")
                    else:
                        total += weight
                if total <= 0 or total > 1.000001:
                    errs.append(f"{sw}: weights must sum to a value in (0, 1]")
    command_skin_weights = stroke.get("command_skin_weights")
    if command_skin_weights is not None:
        if commands is None:
            errs.append(f"{where}.command_skin_weights: requires command-based geometry")
        else:
            coordinate_count = sum(
                1 if command[0] in {"M", "L"} else
                2 if command[0] == "Q" else
                3 if command[0] == "C" else 0
                for command in commands
                if isinstance(command, list) and command and isinstance(command[0], str)
            )
            if not isinstance(command_skin_weights, list) or len(command_skin_weights) != coordinate_count:
                errs.append(
                    f"{where}.command_skin_weights: one influence list per path coordinate pair required "
                    f"({coordinate_count} expected)"
                )
            else:
                for point_index, influences in enumerate(command_skin_weights):
                    sw = f"{where}.command_skin_weights[{point_index}]"
                    if not isinstance(influences, list) or not influences:
                        errs.append(f"{sw}: non-empty influence list required")
                        continue
                    total = 0.0
                    seen_bones = set()
                    for influence_index, influence in enumerate(influences):
                        iw = f"{sw}[{influence_index}]"
                        if not isinstance(influence, dict):
                            errs.append(f"{iw}: must be an object")
                            continue
                        if influence.keys() - {"bone_id", "weight"}:
                            errs.append(f"{iw}: unknown property")
                        bone_id = influence.get("bone_id")
                        if not isinstance(bone_id, str) or not ID_RE.fullmatch(bone_id):
                            errs.append(f"{iw}.bone_id: invalid")
                        elif bone_id in seen_bones:
                            errs.append(f"{iw}.bone_id: duplicate influence")
                        if isinstance(bone_id, str):
                            seen_bones.add(bone_id)
                        weight = influence.get("weight")
                        if not _num(weight) or not 0 <= weight <= 1:
                            errs.append(f"{iw}.weight: number 0..1 required")
                        else:
                            total += weight
                    if total <= 0 or total > 1.000001:
                        errs.append(f"{sw}: weights must sum to a value in (0, 1]")
    if "width" in stroke and (not _num(stroke["width"]) or stroke["width"] <= 0):
        errs.append(f"{where}.width: must be > 0")
    for field, allowed in (
        ("line_cap", {"butt", "round", "square"}),
        ("line_join", {"bevel", "round", "miter"}),
        ("fill_rule", {"nonzero", "evenodd"}),
    ):
        if field in stroke and (
            not isinstance(stroke[field], str) or stroke[field] not in allowed
        ):
            errs.append(f"{where}.{field}: unsupported value")
    if "style_id" in stroke and (
        not isinstance(stroke["style_id"], str) or not ID_RE.fullmatch(stroke["style_id"])
    ):
        errs.append(f"{where}.style_id: invalid")
    dash = stroke.get("dash")
    if dash is not None:
        if not isinstance(dash, list) or not (1 <= len(dash) <= 16):
            errs.append(f"{where}.dash: array of 1..16 required")
        elif not all(_num(v) and v > 0 for v in dash):
            errs.append(f"{where}.dash: all values must be > 0")
    if "dash_offset" in stroke and not _num(stroke["dash_offset"]):
        errs.append(f"{where}.dash_offset: number required")
    holes = stroke.get("holes")
    if holes is not None:
        if not isinstance(holes, list) or len(holes) < 1:
            errs.append(f"{where}.holes: non-empty array required")
        else:
            for i, hole in enumerate(holes):
                if not isinstance(hole, list):
                    errs.append(f"{where}.holes[{i}]: expected path commands array")
                else:
                    _check_path_commands(hole, f"{where}.holes[{i}]", errs)


def _check_studio_data(project, errs):
    styles = project.get("styles", [])
    style_ids = set()
    if not isinstance(styles, list):
        errs.append("styles: must be a list")
    else:
        for index, style in enumerate(styles):
            where = f"styles[{index}]"
            if not isinstance(style, dict):
                errs.append(f"{where}: must be an object")
                continue
            style_id = style.get("id")
            if not isinstance(style_id, str) or not ID_RE.fullmatch(style_id):
                errs.append(f"{where}.id: invalid")
            elif style_id in style_ids:
                errs.append(f"{where}.id: duplicate '{style_id}'")
            else:
                style_ids.add(style_id)
    scenes = project.get("scenes", [])
    scene_ids = {
        scene.get("id") for scene in scenes
        if isinstance(scene, dict) and isinstance(scene.get("id"), str)
    } if isinstance(scenes, list) else set()
    settings = project.get("settings")
    duration = settings.get("duration_frames", 0) if isinstance(settings, dict) else 0
    if not _int(duration) or duration < 1:
        duration = 1

    effects = project.get("effects", [])
    if not isinstance(effects, list):
        errs.append("effects: must be a list")
    else:
        effect_ids = set()
        for index, effect in enumerate(effects):
            where = f"effects[{index}]"
            if not isinstance(effect, dict):
                errs.append(f"{where}: must be an object")
                continue
            for key in effect.keys() - {
                "id", "scene_id", "type", "enabled", "start_frame", "end_frame",
                "intensity", "count", "speed", "color",
            }:
                errs.append(f"{where}.{key}: unknown property")
            effect_id = effect.get("id")
            if not isinstance(effect_id, str) or not ID_RE.fullmatch(effect_id) or effect_id in effect_ids:
                errs.append(f"{where}.id: invalid or duplicate")
            if isinstance(effect_id, str):
                effect_ids.add(effect_id)
            scene_id = effect.get("scene_id")
            if not isinstance(scene_id, str) or scene_id not in scene_ids:
                errs.append(f"{where}.scene_id: scene not found")
            effect_type = effect.get("type")
            if not isinstance(effect_type, str) or effect_type not in {"lightning", "particles", "speed_lines", "camera_shake"}:
                errs.append(f"{where}.type: unsupported effect")
            if "enabled" in effect and not isinstance(effect["enabled"], bool):
                errs.append(f"{where}.enabled: boolean required")
            for field, default in (("start_frame", 0), ("end_frame", duration - 1)):
                value = effect.get(field, default)
                if not _int(value) or value < 0:
                    errs.append(f"{where}.{field}: integer >= 0 required")
            if _int(effect.get("start_frame", 0)) and _int(effect.get("end_frame", duration - 1)):
                if effect.get("start_frame", 0) > effect.get("end_frame", duration - 1):
                    errs.append(f"{where}: start_frame must not exceed end_frame")
            intensity = effect.get("intensity", 0.5)
            if not _num(intensity) or not 0 <= intensity <= 1:
                errs.append(f"{where}.intensity: number 0..1 required")
            if effect_type in {"particles", "speed_lines"}:
                count = effect.get("count", 36)
                if not _int(count) or not 1 <= count <= 200:
                    errs.append(f"{where}.count: integer 1..200 required")
            speed = effect.get("speed", 1)
            if not _num(speed) or not 0 <= speed <= 20:
                errs.append(f"{where}.speed: number 0..20 required")
            color = effect.get("color", "#ffffff")
            if not isinstance(color, str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
                errs.append(f"{where}.color: hex color #RRGGBB required")

    characters = {
        item.get("id"): item for item in project.get("characters", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    } if isinstance(project.get("characters", []), list) else {}
    rigs = project.get("rigs", [])
    if not isinstance(rigs, list):
        errs.append("rigs: must be a list")
    else:
        rig_ids = set()
        rig_characters = set()
        for index, rig in enumerate(rigs):
            where = f"rigs[{index}]"
            if not isinstance(rig, dict):
                errs.append(f"{where}: must be an object")
                continue
            for key in rig.keys() - {"id", "name", "character_id", "bones", "constraints", "animation"}:

                errs.append(f"{where}.{key}: unknown property")
            animation = rig.get("animation")
            if animation is not None:
                aw = f"{where}.animation"
                if not isinstance(animation, dict):
                    errs.append(f"{aw}: must be an object")
                else:
                    for key in animation.keys() - {
                        "type", "enabled", "start_frame", "cycle_frames", "speed",
                        "stride", "bob", "weight", "loop",
                    }:
                        errs.append(f"{aw}.{key}: unknown property")
                    if animation.get("type") != "walk":
                        errs.append(f"{aw}.type: only 'walk' is supported")
                    if "enabled" in animation and not isinstance(animation["enabled"], bool):
                        errs.append(f"{aw}.enabled: boolean required")
                    if "loop" in animation and not isinstance(animation["loop"], bool):
                        errs.append(f"{aw}.loop: boolean required")
                    for field, default in (("start_frame", 0), ("cycle_frames", 24)):
                        value = animation.get(field, default)
                        low, high = (0, None) if field == "start_frame" else (4, 240)
                        if not _int(value) or value < low or (high is not None and value > high):
                            errs.append(f"{aw}.{field}: invalid integer")
                    for field, default, low, high in (
                        ("speed", 1, 0.05, 8), ("stride", 24, 0, 100),
                        ("bob", 5, 0, 30), ("weight", 1, 0, 1),
                    ):
                        value = animation.get(field, default)
                        if not _num(value) or not low <= value <= high:
                            errs.append(f"{aw}.{field}: number {low}..{high} required")
            rig_id = rig.get("id")
            if not isinstance(rig_id, str) or not ID_RE.fullmatch(rig_id) or rig_id in rig_ids:
                errs.append(f"{where}.id: invalid or duplicate")
            if isinstance(rig_id, str):
                rig_ids.add(rig_id)
            if not isinstance(rig.get("name"), str) or not rig["name"].strip():
                errs.append(f"{where}.name: non-empty string required")
            character_id = rig.get("character_id")
            character = characters.get(character_id) if isinstance(character_id, str) else None
            if character is None:
                errs.append(f"{where}.character_id: character not found")
            elif character_id in rig_characters:
                errs.append(f"{where}.character_id: only one active rig per character is supported")
            if isinstance(character_id, str):
                rig_characters.add(character_id)
            bones = rig.get("bones")
            if not isinstance(bones, list):
                errs.append(f"{where}.bones: must be a list")
                continue
            bone_ids = set()
            attached_parts = set()
            for bone_index, bone in enumerate(bones):
                bw = f"{where}.bones[{bone_index}]"
                if not isinstance(bone, dict):
                    errs.append(f"{bw}: must be an object")
                    continue
                for key in bone.keys() - {
                    "id", "name", "parent_id", "character_part_id", "pivot", "rotation",
                    "length", "tracks",
                }:
                    errs.append(f"{bw}.{key}: unknown property")
                bone_id = bone.get("id")
                if not isinstance(bone_id, str) or not ID_RE.fullmatch(bone_id) or bone_id in bone_ids:
                    errs.append(f"{bw}.id: invalid or duplicate")
                if isinstance(bone_id, str):
                    bone_ids.add(bone_id)
                if not isinstance(bone.get("name"), str) or not bone["name"].strip():
                    errs.append(f"{bw}.name: non-empty string required")
                parent = bone.get("parent_id")
                if parent is not None and (not isinstance(parent, str) or parent == bone_id):
                    errs.append(f"{bw}.parent_id: invalid")
                part_id = bone.get("character_part_id")
                parts = character.get("parts", []) if isinstance(character, dict) else []
                parts = parts if isinstance(parts, list) else []
                if not isinstance(part_id, str):
                    errs.append(f"{bw}.character_part_id: character part not found")
                elif not any(isinstance(part, dict) and part.get("id") == part_id for part in parts):
                    errs.append(f"{bw}.character_part_id: character part not found")
                else:
                    if part_id in attached_parts:
                        errs.append(f"{bw}.character_part_id: each character part can attach to one bone")
                    attached_parts.add(part_id)
                if "rotation" in bone and (
                    not _num(bone["rotation"]) or not -3600 <= bone["rotation"] <= 3600
                ):
                    errs.append(f"{bw}.rotation: number -3600..3600 required")
                if "length" in bone and (
                    not _num(bone["length"]) or bone["length"] < 0
                ):
                    errs.append(f"{bw}.length: number >= 0 required")
                pivot = bone.get("pivot")
                if not isinstance(pivot, dict) or any(
                    not _num(pivot.get(axis)) or not -8192 <= pivot[axis] <= 8192
                    for axis in ("x", "y")
                ):
                    errs.append(f"{bw}.pivot: x and y between -8192 and 8192 required")
                elif pivot.keys() - {"x", "y"}:
                    errs.append(f"{bw}.pivot: unknown property")
                tracks = bone.get("tracks", {})
                if not isinstance(tracks, dict) or any(channel != "rotation" for channel in tracks):
                    errs.append(f"{bw}.tracks: only rotation tracks are supported")
                else:
                    _check_tracks(tracks, f"{bw}.tracks", errs)
            for bone_index, bone in enumerate(bones):
                if isinstance(bone, dict):
                    parent_id = bone.get("parent_id")
                    if isinstance(parent_id, str) and parent_id not in bone_ids:
                        errs.append(f"{where}.bones[{bone_index}].parent_id: bone not found")
            parent_map = {
                bone.get("id"): bone.get("parent_id")
                for bone in bones
                if isinstance(bone, dict) and isinstance(bone.get("id"), str)
                and (bone.get("parent_id") is None or isinstance(bone.get("parent_id"), str))
            }
            for bone_id in parent_map:
                seen = set()
                parent_id = bone_id
                while parent_id in parent_map and parent_map[parent_id] is not None:
                    if parent_id in seen:
                        errs.append(f"{where}.bones: parent relationships must not contain cycles")
                        break
                    seen.add(parent_id)
                    parent_id = parent_map[parent_id]
            constraints = rig.get("constraints", [])
            if not isinstance(constraints, list):
                errs.append(f"{where}.constraints: must be a list")
            else:
                for constraint_index, constraint in enumerate(constraints):
                    cw = f"{where}.constraints[{constraint_index}]"
                    if not isinstance(constraint, dict):
                        errs.append(f"{cw}: must be an object")
                        continue
                    for field in ("bone_id", "target_bone_id"):
                        bone_id = constraint.get(field)
                        if bone_id is not None and bone_id not in bone_ids:
                            errs.append(f"{cw}.{field}: bone not found")

    # Weighted vector strokes must reference bones that actually exist in the project.
    rig_list = rigs if isinstance(rigs, list) else []
    known_bone_ids = {
        bone.get("id")
        for rig in rig_list if isinstance(rig, dict)
        for bone in (rig.get("bones", []) if isinstance(rig.get("bones", []), list) else [])
        if isinstance(bone, dict) and isinstance(bone.get("id"), str)
    }

    def _check_skin_references(strokes, where):
        if not isinstance(strokes, list):
            return
        for stroke_index, stroke in enumerate(strokes):
            if not isinstance(stroke, dict):
                continue
            for weight_field in ("skin_weights", "command_skin_weights"):
                if not isinstance(stroke.get(weight_field), list):
                    continue
                for point_index, influences in enumerate(stroke[weight_field]):
                    if not isinstance(influences, list):
                        continue
                    for influence_index, influence in enumerate(influences):
                        if not isinstance(influence, dict):
                            continue
                        bone_id = influence.get("bone_id")
                        if isinstance(bone_id, str) and bone_id not in known_bone_ids:
                            errs.append(
                                f"{where}[{stroke_index}].{weight_field}[{point_index}]"
                                f"[{influence_index}].bone_id: rig bone not found"
                            )

    project_drawings = project.get("drawings", {})
    if isinstance(project_drawings, dict):
        for drawing_id, drawing in project_drawings.items():
            if isinstance(drawing, dict):
                _check_skin_references(drawing.get("strokes"), f"drawings.{drawing_id}.strokes")
    for character_index, character in enumerate(project.get("characters", [])):
        if not isinstance(character, dict) or not isinstance(character.get("parts"), list):
            continue
        for part_index, part in enumerate(character["parts"]):
            if isinstance(part, dict):
                _check_skin_references(
                    part.get("strokes"),
                    f"characters[{character_index}].parts[{part_index}].strokes",
                )

    audio = project.get("audio", [])
    if not isinstance(audio, list):
        errs.append("audio: must be a list")
    else:
        audio_ids = set()
        for index, clip in enumerate(audio):
            where = f"audio[{index}]"
            if not isinstance(clip, dict):
                errs.append(f"{where}: must be an object")
                continue
            for key in clip.keys() - {
                "id", "name", "filename", "mime_type", "url", "start_frame",
                "offset_seconds", "volume", "duration_frames",
            }:
                errs.append(f"{where}.{key}: unknown property")
            clip_id = clip.get("id")
            if not isinstance(clip_id, str) or not ID_RE.fullmatch(clip_id) or clip_id in audio_ids:
                errs.append(f"{where}.id: invalid or duplicate")
            if isinstance(clip_id, str):
                audio_ids.add(clip_id)
            for field in ("filename", "mime_type"):
                if not isinstance(clip.get(field), str) or not clip[field]:
                    errs.append(f"{where}.{field}: non-empty string required")
            filename = clip.get("filename")
            file_match = re.fullmatch(
                r"([A-Za-z0-9_-]{1,64})\.(aac|m4a|mp3|ogg|wav|webm)",
                filename if isinstance(filename, str) else "",
            )
            if not file_match or file_match.group(1) != clip_id:
                errs.append(f"{where}.filename: must be the clip ID and a supported audio extension")
            elif clip.get("mime_type") != {
                "aac": "audio/aac", "m4a": "audio/mp4", "mp3": "audio/mpeg",
                "ogg": "audio/ogg", "wav": "audio/wav", "webm": "audio/webm",
            }[file_match.group(2)]:
                errs.append(f"{where}.mime_type: does not match the audio filename")
            if "url" in clip and clip["url"] != f"/api/projects/{project.get('id')}/audio/{clip_id}":
                errs.append(f"{where}.url: must use the project audio endpoint")
            if not isinstance(clip.get("name"), str) or not clip["name"].strip():
                errs.append(f"{where}.name: non-empty string required")
            start = clip.get("start_frame", 0)
            if not _int(start) or start < 0:
                errs.append(f"{where}.start_frame: integer >= 0 required")
            offset = clip.get("offset_seconds", 0)
            if not _num(offset) or offset < 0:
                errs.append(f"{where}.offset_seconds: number >= 0 required")
            volume = clip.get("volume", 1)
            if not _num(volume) or not 0 <= volume <= 1:
                errs.append(f"{where}.volume: number 0..1 required")
            if "duration_frames" in clip and (
                not _int(clip["duration_frames"]) or clip["duration_frames"] < 1
            ):
                errs.append(f"{where}.duration_frames: integer >= 1 required")


def validate_character_document(character):
    errs = []
    if not isinstance(character, dict):
        return ["character: must be an object"]
    allowed_character_fields = {"format", "version", "id", "name", "scene_id", "parts"}
    for key in character.keys() - allowed_character_fields:
        errs.append(f"character.{key}: unknown property")
    if character.get("format") != "kae-character":
        errs.append("character.format: must be 'kae-character'")
    if not _int(character.get("version")) or character["version"] != 1:
        errs.append("character.version: supported version is 1")
    character_id = character.get("id")
    if not isinstance(character_id, str) or not ID_RE.fullmatch(character_id):
        errs.append("character.id: invalid")
    if not isinstance(character.get("name"), str) or not character["name"].strip():
        errs.append("character.name: non-empty string required")
    if "scene_id" in character and (
        not isinstance(character["scene_id"], str)
        or not ID_RE.fullmatch(character["scene_id"])
    ):
        errs.append("character.scene_id: invalid")
    parts = character.get("parts")
    if not isinstance(parts, list) or not parts:
        errs.append("character.parts: non-empty list required")
        return errs[:MAX_ERRORS]

    part_ids = set()
    for index, part in enumerate(parts):
        where = f"character.parts[{index}]"
        if not isinstance(part, dict):
            errs.append(f"{where}: must be an object")
            continue
        allowed_part_fields = {"id", "name", "strokes", "transform", "tracks", "depth"}
        for key in part.keys() - allowed_part_fields:
            errs.append(f"{where}.{key}: unknown property")
        part_id = part.get("id")
        if not isinstance(part_id, str) or not ID_RE.fullmatch(part_id):
            errs.append(f"{where}.id: invalid")
        elif part_id in part_ids:
            errs.append(f"{where}.id: duplicate '{part_id}'")
        else:
            part_ids.add(part_id)
        if not isinstance(part.get("name"), str) or not part["name"].strip():
            errs.append(f"{where}.name: non-empty string required")
        drawing = {"id": "part", "strokes": part.get("strokes")}
        _check_drawings({"part": drawing}, errs)
        strokes = part.get("strokes")
        if isinstance(strokes, list):
            stroke_ids = set()
            for stroke_index, stroke in enumerate(strokes):
                stroke_where = f"{where}.strokes[{stroke_index}]"
                if not isinstance(stroke, dict):
                    continue
                for key in stroke.keys() - {
                    "id", "tool", "color", "width", "opacity", "closed", "fill", "smoothing",
                    "points", "commands", "fill_rule", "line_cap", "line_join",
                    "style_id", "dash", "dash_offset", "holes",
                }:
                    errs.append(f"{stroke_where}.{key}: unknown property")
                stroke_id = stroke.get("id")
                if isinstance(stroke_id, str):
                    if stroke_id in stroke_ids:
                        errs.append(f"{stroke_where}.id: duplicate '{stroke_id}'")
                    stroke_ids.add(stroke_id)
                if "tool" in stroke and (
                    not isinstance(stroke["tool"], str)
                    or stroke["tool"] not in {"brush", "pen", "eraser"}
                ):
                    errs.append(f"{stroke_where}.tool: invalid")
                for color_key in ("color", "fill"):
                    color = stroke.get(color_key)
                    if color_key in stroke and color is not None and (
                        not isinstance(color, str)
                        or not re.fullmatch(r"#[0-9A-Fa-f]{6}(?:[0-9A-Fa-f]{2})?", color)
                    ):
                        errs.append(f"{stroke_where}.{color_key}: invalid color")
                for number_key, low, high in (("opacity", 0, 1), ("smoothing", 0, 1)):
                    if number_key in stroke and (
                        not _num(stroke[number_key]) or not low <= stroke[number_key] <= high
                    ):
                        errs.append(f"{stroke_where}.{number_key}: number {low}..{high} required")
                if "closed" in stroke and not isinstance(stroke["closed"], bool):
                    errs.append(f"{stroke_where}.closed: boolean required")
        transform = part.get("transform", {})
        if not isinstance(transform, dict):
            errs.append(f"{where}.transform: must be an object")
        else:
            for key in transform.keys() - {
                "x", "y", "rotation", "scale_x", "scale_y", "anchor_x", "anchor_y"
            }:
                errs.append(f"{where}.transform.{key}: unknown channel")
            for channel in ("x", "y", "rotation", "scale_x", "scale_y", "anchor_x", "anchor_y"):
                if channel in transform and not _num(transform[channel]):
                    errs.append(f"{where}.transform.{channel}: number required")
        if "tracks" in part:
            _check_tracks(part["tracks"], f"{where}.tracks", errs)
        if "depth" in part and (
            not _num(part["depth"]) or not 0 <= part["depth"] <= 2
        ):
            errs.append(f"{where}.depth: number 0..2 required")
    return errs[:MAX_ERRORS]


def _check_exposures(exps, where, drawings, errs):
    if not isinstance(exps, list):
        errs.append(f"{where}: exposures must be a list")
        return
    spans = []
    for i, e in enumerate(exps):
        w = f"{where}[{i}]"
        if not isinstance(e, dict):
            errs.append(f"{w}: must be an object")
            continue
        s, n, d = e.get("start"), e.get("length"), e.get("drawing")
        if not _int(s) or s < 0:
            errs.append(f"{w}.start: integer >= 0 required")
        if not _int(n) or n < 1:
            errs.append(f"{w}.length: integer >= 1 required")
        if d not in drawings:
            errs.append(f"{w}.drawing: '{d}' does not exist")
        if _int(s) and _int(n):
            spans.append((s, s + n, i))
    spans.sort()
    for a, b in zip(spans, spans[1:]):
        if b[0] < a[1]:
            errs.append(f"{where}[{b[2]}]: overlaps exposure [{a[2]}]")


def _check_layer(ly, where, layer_ids, drawings, errs, ancestors=None):
    """Validate a single layer recursively. ancestors tracks group IDs for cycle detection."""
    if ancestors is None:
        ancestors = set()
    if not isinstance(ly, dict):
        errs.append(f"{where}: must be an object")
        return
    lid = ly.get("id")
    if not isinstance(lid, str) or not ID_RE.match(lid):
        errs.append(f"{where}.id: invalid")
    elif lid in layer_ids:
        errs.append(f"{where}.id: duplicate '{lid}'")
    else:
        layer_ids.add(lid)
    layer_type = ly.get("type")
    if layer_type not in ("drawing", "group", "character_instance"):
        errs.append(f"{where}.type: must be 'drawing', 'group', or 'character_instance'")
    if "depth" in ly and (not _num(ly["depth"]) or not 0 <= ly["depth"] <= 2):
        errs.append(f"{where}.depth: number 0..2 required")
    character_id = ly.get("character_id")
    part_id = ly.get("character_part_id")
    if character_id is not None and (
        not isinstance(character_id, str) or not ID_RE.fullmatch(character_id)
    ):
        errs.append(f"{where}.character_id: invalid")
    if part_id is not None and (
        not isinstance(part_id, str) or not ID_RE.fullmatch(part_id)
    ):
        errs.append(f"{where}.character_part_id: invalid")
    if (character_id is None) != (part_id is None):
        errs.append(f"{where}: character_id and character_part_id must appear together")
    if "opacity" in ly and (not _num(ly["opacity"]) or not 0 <= ly["opacity"] <= 1):
        errs.append(f"{where}.opacity: 0..1 required")
    transform = ly.get("transform", {})
    if isinstance(transform, dict) and "rotation_y" in transform and (
        not _num(transform["rotation_y"]) or not -180 <= transform["rotation_y"] <= 180
    ):
        errs.append(f"{where}.transform.rotation_y: number -180..180 required")
    if "exposures" in ly:
        _check_exposures(ly["exposures"], f"{where}.exposures", drawings, errs)
    if "tracks" in ly:
        _check_tracks(ly["tracks"], f"{where}.tracks", errs)
        tracks = ly["tracks"]
        if isinstance(tracks, dict) and isinstance(tracks.get("rotation_y"), list):
            for index, keyframe in enumerate(tracks["rotation_y"]):
                if isinstance(keyframe, dict) and _num(keyframe.get("v")) and not -180 <= keyframe["v"] <= 180:
                    errs.append(f"{where}.tracks.rotation_y[{index}].v: number -180..180 required")
    if layer_type in ("group", "character_instance"):
        if lid in ancestors:
            errs.append(f"{where}: cycle detected (ancestor '{lid}')")
            return
        children = ly.get("children")
        if children is not None:
            if not isinstance(children, list):
                errs.append(f"{where}.children: must be a list")
            else:
                new_ancestors = ancestors | ({lid} if isinstance(lid, str) else set())
                for ci, child in enumerate(children):
                    _check_layer(child, f"{where}.children[{ci}]", layer_ids, drawings, errs, new_ancestors)
    if layer_type == "character_instance":
        overrides = ly.get("instance_overrides")
        if overrides is not None:
            if not isinstance(overrides, dict):
                errs.append(f"{where}.instance_overrides: must be an object")
            else:
                if "opacity" in overrides and (not _num(overrides["opacity"]) or not 0 <= overrides["opacity"] <= 1):
                    errs.append(f"{where}.instance_overrides.opacity: 0..1 required")
                if "visible" in overrides and not isinstance(overrides["visible"], bool):
                    errs.append(f"{where}.instance_overrides.visible: must be boolean")


def _check_scenes(scenes, drawings, errs):
    if not isinstance(scenes, list) or not scenes:
        errs.append("scenes: non-empty list required")
        return
    scene_ids, layer_ids = set(), set()
    for si, sc in enumerate(scenes):
        sw = f"scenes[{si}]"
        if not isinstance(sc, dict):
            errs.append(f"{sw}: must be an object")
            continue
        sid = sc.get("id")
        if not isinstance(sid, str) or not ID_RE.match(sid):
            errs.append(f"{sw}.id: invalid")
        elif sid in scene_ids:
            errs.append(f"{sw}.id: duplicate '{sid}'")
        scene_ids.add(sid)
        layers = sc.get("layers")
        if not isinstance(layers, list):
            errs.append(f"{sw}.layers: must be a list")
            layers = []
        for li, ly in enumerate(layers):
            _check_layer(ly, f"{sw}.layers[{li}]", layer_ids, drawings, errs)

        cam = sc.get("camera")
        if cam is not None:
            if not isinstance(cam, dict):
                errs.append(f"{sw}.camera: must be an object")
            else:
                transform = cam.get("transform", {})
                if not isinstance(transform, dict):
                    errs.append(f"{sw}.camera.transform: must be an object")
                else:
                    for channel in ("x", "y"):
                        if channel in transform and (
                            not _num(transform[channel]) or not -8192 <= transform[channel] <= 8192
                        ):
                            errs.append(f"{sw}.camera.transform.{channel}: number -8192..8192 required")
                    if "rotation" in transform and (
                        not _num(transform["rotation"]) or not -3600 <= transform["rotation"] <= 3600
                    ):
                        errs.append(f"{sw}.camera.transform.rotation: number -3600..3600 required")
                    for channel in ("scale_x", "scale_y"):
                        if channel in transform and (
                            not _num(transform[channel])
                            or not 0.05 <= transform[channel] <= 32
                        ):
                            errs.append(f"{sw}.camera.transform.{channel}: number 0.05..32 required")
                if "tracks" in cam:
                    tracks = cam["tracks"]
                    if not isinstance(tracks, dict):
                        errs.append(f"{sw}.camera.tracks: tracks must be an object")
                    else:
                        for channel in tracks:
                            if channel not in CAMERA_CHANNELS:

                                errs.append(f"{sw}.camera.tracks.{channel}: unknown camera channel")
                        _check_tracks(
                            tracks, f"{sw}.camera.tracks", errs, CAMERA_CHANNELS
                        )
                        for channel, keyframes in tracks.items():
                            if channel not in CAMERA_CHANNELS or not isinstance(keyframes, list):
                                continue
                            bounds = {
                                "x": (-8192, 8192), "y": (-8192, 8192),
                                "rotation": (-3600, 3600), "rotation_x": (-3600, 3600),
                                "rotation_y": (-3600, 3600), "scale_x": (0.05, 32),
                                "scale_y": (0.05, 32), "fov": (1, 179),
                                "focus_distance": (0, math.inf), "aperture": (0, 1),
                            }
                            if channel not in bounds:
                                continue
                            lo, hi = bounds[channel]

                            for index, keyframe in enumerate(keyframes):
                                if (
                                    isinstance(keyframe, dict)
                                    and _num(keyframe.get("v"))
                                    and not lo <= keyframe["v"] <= hi
                                ):
                                    errs.append(f"{sw}.camera.tracks.{channel}[{index}].v: number {lo}..{hi} required")
        lights = sc.get("lights", [])
        if not isinstance(lights, list):
            errs.append(f"{sw}.lights: must be a list")
        else:
            light_ids = set()
            for li, light in enumerate(lights):
                lw = f"{sw}.lights[{li}]"
                if not isinstance(light, dict):
                    errs.append(f"{lw}: must be an object")
                    continue
                light_id = light.get("id")
                if not isinstance(light_id, str) or not ID_RE.match(light_id):
                    errs.append(f"{lw}.id: invalid or duplicate")
                elif light_id in light_ids:
                    errs.append(f"{lw}.id: invalid or duplicate")
                else:
                    light_ids.add(light_id)
                for channel, low, high in (("x", -8192, 8192), ("y", -8192, 8192)):
                    if not _num(light.get(channel)) or not low <= light[channel] <= high:
                        errs.append(f"{lw}.{channel}: number {low}..{high} required")
                if not _num(light.get("radius")) or not 16 <= light["radius"] <= 8192:
                    errs.append(f"{lw}.radius: number 16..8192 required")
                if not _num(light.get("intensity")) or not 0 <= light["intensity"] <= 1:
                    errs.append(f"{lw}.intensity: number 0..1 required")
                color = light.get("color")
                if not isinstance(color, str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
                    errs.append(f"{lw}.color: hex color #RRGGBB required")


def _check_preview_range(project, errs):
    preview = project.get("preview_range")
    if preview is None:
        return
    if not isinstance(preview, dict):
        errs.append("preview_range: must be an object")
        return
    start, end = preview.get("start"), preview.get("end")
    total = project.get("settings", {}).get("duration_frames", 1) if isinstance(project.get("settings"), dict) else 1
    if not _int(start) or not 0 <= start < total:
        errs.append("preview_range.start: must be within the project timeline")
    if not _int(end) or not 0 <= end < total:
        errs.append("preview_range.end: must be within the project timeline")
    if _int(start) and _int(end) and start > end:
        errs.append("preview_range: start must be less than or equal to end")


def _check_markers(project, errs):
    markers = project.get("markers", [])
    if not isinstance(markers, list):
        errs.append("markers: must be a list")
        return
    total = project.get("settings", {}).get("duration_frames", 1) if isinstance(project.get("settings"), dict) else 1
    seen_ids = set()
    seen_positions = set()
    for index, marker in enumerate(markers):
        where = f"markers[{index}]"
        if not isinstance(marker, dict):
            errs.append(f"{where}: must be an object")
            continue
        marker_id = marker.get("id")
        if not isinstance(marker_id, str) or not ID_RE.fullmatch(marker_id) or marker_id in seen_ids:
            errs.append(f"{where}.id: must be a unique valid ID")
        else:
            seen_ids.add(marker_id)
        frame = marker.get("frame")
        if not _int(frame) or frame < 0 or frame >= total:
            errs.append(f"{where}.frame: must be within the project timeline (0..{max(0, total - 1)})")
        name = marker.get("name")
        if not isinstance(name, str) or not name.strip() or len(name) > 120:
            errs.append(f"{where}.name: non-empty string up to 120 characters required")
        if isinstance(frame, int) and not isinstance(frame, bool) and (frame, str(name).casefold()) in seen_positions:
            errs.append(f"{where}: duplicate marker name on the same frame")
        elif isinstance(frame, int) and not isinstance(frame, bool):
            seen_positions.add((frame, str(name).casefold()))
        color = marker.get("color")
        if color is not None and (not isinstance(color, str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", color)):
            errs.append(f"{where}.color: hex color #RRGGBB required")


def validate_project(p):
    errs = []
    if not isinstance(p, dict):
        return ["project: must be an object"]
    schema_valid, schema_error = schema_validator.validate_project(p)
    if not schema_valid:
        errs.append(f"schema: {schema_error}")
    if p.get("format") != "kae":
        errs.append("format: must be 'kae'")
    if not _int(p.get("version")) or p["version"] < 1:
        errs.append("version: integer >= 1 required")
    if not isinstance(p.get("id"), str) or not ID_RE.match(p["id"]):
        errs.append("id: invalid")
    if not isinstance(p.get("name"), str) or not p["name"].strip():
        errs.append("name: non-empty string required")
    _check_settings(p.get("settings"), errs)
    _check_preview_range(p, errs)
    _check_markers(p, errs)
    _check_drawings(p.get("drawings"), errs)
    characters = p.get("characters", [])
    if not isinstance(characters, list):
        errs.append("characters: must be a list")
    else:
        character_ids = set()
        for index, character in enumerate(characters):
            if isinstance(character, dict) and character.get("format") == "kae-character":
                errs.extend(
                    f"characters[{index}].{error.removeprefix('character.')}"
                    for error in validate_character_document(character)
                )
            elif not isinstance(character, dict) or not isinstance(character.get("id"), str):
                errs.append(f"characters[{index}]: must have a valid id")
            character_id = character.get("id") if isinstance(character, dict) else None
            if isinstance(character_id, str):
                if character_id in character_ids:
                    errs.append(f"characters[{index}].id: duplicate '{character_id}'")
                character_ids.add(character_id)
    drawings = p.get("drawings") if isinstance(p.get("drawings"), dict) else {}
    _check_scenes(p.get("scenes"), drawings, errs)
    _check_studio_data(p, errs)
    return errs[:MAX_ERRORS]
