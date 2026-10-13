"""Assemble procedural face features from shared layout."""
from engine.characters.face.ears import ear_shape
from engine.characters.face.eyes import eye_shape
from engine.characters.face.facial_layout import layout_features
from engine.characters.face.head_shape import head_outline
from engine.characters.face.mouth import mouth_shape


def generate_face(center, width, height, *, expression=None):
    layout = layout_features(center, width, height)
    openness = (expression or {}).get("eye_open", 1.0)
    mouth_open = (expression or {}).get("mouth_open", 0.0) * width * 0.2
    smile = (expression or {}).get("smile", 0.0)
    return {
        "head": head_outline(center, width, height),
        "eyes": [eye_shape(layout[key], width * 0.22, height * 0.12, openness=openness)
                 for key in ("left_eye", "right_eye")],
        "mouth": mouth_shape(layout["mouth"], width * 0.3, mouth_open, smile),
        "ears": [ear_shape(layout[key], width * 0.12, height * 0.15, side=side)
                 for key, side in (("left_ear", -1), ("right_ear", 1))],
        "landmarks": layout,
    }
