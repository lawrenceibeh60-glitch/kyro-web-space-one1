"""Create editable rig skeletons from character part documents."""
from engine.core.identifiers import new_id
from engine.rigging.rig_validation import validate_rig


def build_rig(character, *, name=None):
    if not isinstance(character, dict) or not isinstance(character.get("id"), str):
        raise ValueError("A character with a stable id is required")
    bones = []
    for part in character.get("parts", []):
        part_id = part.get("id")
        transform = part.get("transform", {})
        pivot = {"x": transform.get("x", 0), "y": transform.get("y", 0)}
        bones.append({
            "id": f"bone_{part_id}"[:64], "name": part.get("name", part_id),
            "character_part_id": part_id, "parent_id": None,
            "pivot": pivot, "rotation": 0,
        })
    rig = {"id": new_id("rig"), "name": name or f"{character.get('name', character['id'])} Rig",
           "character_id": character["id"], "bones": bones}
    errors = validate_rig(rig, character)
    if errors:
        raise ValueError("; ".join(errors))
    return rig
