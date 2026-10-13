"""Validate rig structure and character-part references."""


def validate_rig(rig, character=None):
    errors = []
    if not isinstance(rig, dict):
        return ["rig: must be an object"]
    bones = rig.get("bones")
    if not isinstance(bones, list):
        return ["rig.bones: must be a list"]
    ids, parts = set(), set()
    character_parts = {
        part.get("id") for part in (character or {}).get("parts", [])
        if isinstance(part, dict)
    }
    for index, bone in enumerate(bones):
        path = f"rig.bones[{index}]"
        if not isinstance(bone, dict):
            errors.append(f"{path}: must be an object")
            continue
        bone_id = bone.get("id")
        if not isinstance(bone_id, str) or not bone_id or bone_id in ids:
            errors.append(f"{path}.id: missing or duplicate")
        ids.add(bone_id)
        part_id = bone.get("character_part_id")
        if character is not None and part_id not in character_parts:
            errors.append(f"{path}.character_part_id: character part not found")
        if part_id in parts:
            errors.append(f"{path}.character_part_id: only one bone per part is supported")
        parts.add(part_id)
        pivot = bone.get("pivot")
        if not isinstance(pivot, dict) or not all(isinstance(pivot.get(axis), (int, float)) for axis in ("x", "y")):
            errors.append(f"{path}.pivot: finite x and y required")
    for index, bone in enumerate(bones):
        if isinstance(bone, dict) and bone.get("parent_id") is not None and bone["parent_id"] not in ids:
            errors.append(f"rig.bones[{index}].parent_id: bone not found")
    if not errors:
        try:
            from engine.rigging.skeleton import Skeleton
            Skeleton(bones)
        except ValueError as error:
            errors.append(str(error))
    return errors
