"""Camera zoom limits and pointer-anchored zoom behavior."""
import math

MIN_ZOOM, MAX_ZOOM = 0.05, 32.0


def clamp_zoom(value, low=MIN_ZOOM, high=MAX_ZOOM):
    if low <= 0 or high < low:
        raise ValueError("Zoom limits must be positive and ordered")
    return max(low, min(high, float(value)))


def zoom_at(camera, screen_point, factor, *, viewport=(0, 0)):
    from engine.camera.camera_transform import screen_to_world, world_to_screen
    updated = dict(camera)
    anchor = screen_to_world(screen_point, updated, viewport=viewport)
    zoom = clamp_zoom(updated.get("scale_x", updated.get("zoom", 1)) * factor)
    updated["scale_x"] = updated["scale_y"] = zoom
    projected = world_to_screen(anchor, updated, viewport=viewport)
    updated["x"] += projected[0] - screen_point[0]
    updated["y"] += projected[1] - screen_point[1]
    return updated


def logarithmic_zoom(current, wheel_delta, sensitivity=0.0015):
    return clamp_zoom(current * math.exp(-wheel_delta * sensitivity))
