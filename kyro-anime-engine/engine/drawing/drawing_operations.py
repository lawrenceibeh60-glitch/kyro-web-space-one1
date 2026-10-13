"""Non-mutating vector drawing transformations."""
from copy import deepcopy
from engine.core.identifiers import new_id


def transform_stroke(stroke, *, x=0, y=0, scale_x=1, scale_y=1, rotation=0, origin=(0, 0)):
    import math
    result = deepcopy(stroke)
    radians = math.radians(rotation)
    cosine, sine = math.cos(radians), math.sin(radians)
    ox, oy = origin
    for point in result.get("points", []):
        px, py = (point[0] - ox) * scale_x, (point[1] - oy) * scale_y
        point[0] = ox + x + px * cosine - py * sine
        point[1] = oy + y + px * sine + py * cosine
    return result


def duplicate_stroke(stroke, *, dx=0, dy=0):
    result = transform_stroke(stroke, x=dx, y=dy)
    result["id"] = new_id("stroke")
    return result


def delete_strokes(drawing, stroke_ids):
    removed = set(stroke_ids)
    return {**drawing, "strokes": [stroke for stroke in drawing.get("strokes", []) if stroke.get("id") not in removed]}


def reverse_stroke(stroke):
    result = deepcopy(stroke)
    result["points"] = list(reversed(result.get("points", [])))
    return result
