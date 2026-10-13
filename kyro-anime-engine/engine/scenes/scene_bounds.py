"""Compute scene bounds from visible drawings and layer transforms."""
from engine.math.bounding_boxes import from_points, union


def scene_bounds(scene, drawings, *, frame=0, visible_only=True):
    bounds = None
    for layer in scene.get("layers", []):
        if visible_only and not layer.get("visible", True):
            continue
        for exposure in layer.get("exposures", []):
            if not exposure.get("start", 0) <= frame < exposure.get("start", 0) + exposure.get("length", 1):
                continue
            drawing = drawings.get(exposure.get("drawing"), {})
            points = [point[:2] for stroke in drawing.get("strokes", []) for point in stroke.get("points", [])]
            current = from_points(points)
            if current is None:
                continue
            transform = layer.get("transform", {})
            dx, dy = transform.get("x", 0), transform.get("y", 0)
            current = (current[0] + dx, current[1] + dy, current[2] + dx, current[3] + dy)
            bounds = union(bounds, current)
    return bounds
