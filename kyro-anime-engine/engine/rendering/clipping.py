"""Viewport clipping facade for vector line and polygon commands."""
from engine.geometry.clipping import clip_polygon, clip_segment


def clip_command(command, bounds):
    kind = getattr(command, "kind", None) if not isinstance(command, dict) else command.get("kind")
    points = getattr(command, "points", None) if not isinstance(command, dict) else command.get("points")
    if not points:
        return None
    if kind in {"polygon", "fill"}:
        clipped = clip_polygon(points, bounds)
        if len(clipped) < 3:
            return None
    else:
        clipped = []
        for start, end in zip(points, points[1:]):
            segment = clip_segment(start, end, bounds)
            if segment:
                clipped.extend(segment)
        if not clipped:
            return None
    if isinstance(command, dict):
        return {**command, "points": clipped}
    from dataclasses import replace
    return replace(command, points=clipped)
