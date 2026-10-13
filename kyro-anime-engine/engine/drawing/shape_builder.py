"""Generate editor-compatible strokes for common vector shapes."""
from engine.core.identifiers import new_id
from engine.geometry.primitives import ellipse, rectangle, regular_polygon


def shape_stroke(points, color="#111111", width=3, *, fill=None, closed=True, tool="shape"):
    stroke = {"id": new_id("stroke"), "tool": tool, "color": color, "width": width,
              "points": [[x, y, 1] for x, y in points], "closed": closed}
    if fill is not None:
        stroke["fill"] = fill
    return stroke


def rectangle_stroke(x, y, width, height, **style):
    return shape_stroke(rectangle(x, y, width, height), **style)


def ellipse_stroke(cx, cy, rx, ry=None, *, segments=32, **style):
    return shape_stroke(ellipse(cx, cy, rx, ry, segments=segments), **style)


def polygon_stroke(cx, cy, radius, sides, *, rotation=0, **style):
    return shape_stroke(regular_polygon(cx, cy, radius, sides, rotation=rotation), **style)
