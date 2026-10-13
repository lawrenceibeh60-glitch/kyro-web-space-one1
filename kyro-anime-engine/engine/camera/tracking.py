"""Camera tracking helpers that center a target with optional smoothing."""
from engine.math.numerical import clamp


def track_target(camera, target, viewport, *, weight=1.0):
    weight = clamp(weight, 0.0, 1.0)
    zoom = camera.get("zoom", camera.get("scale_x", 1.0))
    desired = (target[0] - viewport[0] / (2 * zoom),
               target[1] - viewport[1] / (2 * zoom))
    return {
        **camera,
        "x": camera.get("x", 0) + (desired[0] - camera.get("x", 0)) * weight,
        "y": camera.get("y", 0) + (desired[1] - camera.get("y", 0)) * weight,
    }


def follow_path(camera, targets, viewport, *, weight=1.0):
    result = dict(camera)
    for target in targets:
        result = track_target(result, target, viewport, weight=weight)
    return result
