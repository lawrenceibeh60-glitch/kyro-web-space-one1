"""Evaluate a camera path with the shared animation track evaluator."""
from engine.animation.interpolation import evaluate_track


def evaluate_camera_path(tracks, frame, transform=None):
    result = {"x": 0, "y": 0, "rotation": 0, "scale_x": 1, "scale_y": 1}
    result.update(transform or {})
    channels = {"x": "x", "y": "y", "rotation": "rotation", "scale_x": "scale_x", "scale_y": "scale_y"}
    for channel, default in result.items():
        if channel in channels and tracks.get(channel):
            result[channel] = evaluate_track(tracks[channel], frame, default)
    result["zoom"] = result["scale_x"]
    return result
