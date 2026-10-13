"""Compose a normalized body from anatomy proportions."""
from engine.characters.proportions import normalize_proportions


def generate_body(proportions=None, origin=(0, 0)):
    p = normalize_proportions(proportions)
    x, y = origin
    head, torso, leg = p["head"], p["torso"], p["leg"]
    top = y
    head_bottom = top + head
    torso_bottom = head_bottom + torso
    return {
        "head": {"center": (x, top + head / 2), "height": head},
        "torso": {"top": head_bottom, "bottom": torso_bottom, "width": p["shoulder_width"]},
        "legs": {"top": torso_bottom, "bottom": torso_bottom + leg, "width": p["hip_width"]},
        "height": head + torso + leg,
    }
