"""Fit world bounds into a viewport while preserving aspect ratio."""
from engine.camera.zoom import clamp_zoom


def frame_bounds(bounds, viewport, *, padding=0.9):
    if bounds is None:
        raise ValueError("Cannot frame empty bounds")
    width, height = viewport
    if width <= 0 or height <= 0 or not 0 < padding <= 1:
        raise ValueError("Viewport dimensions and padding must be positive")
    min_x, min_y, max_x, max_y = bounds
    world_w, world_h = max(max_x - min_x, 1e-9), max(max_y - min_y, 1e-9)
    zoom = clamp_zoom(min(width / world_w, height / world_h) * padding)
    return {
        "x": (min_x + max_x) / 2,
        "y": (min_y + max_y) / 2,
        "zoom": zoom,
        "rotation": 0,
    }
