"""Evaluate transform tracks for a layer at a timeline frame."""
from engine.animation.interpolation import evaluate_track

DEFAULT_TRANSFORM = {"x": 0, "y": 0, "rotation": 0, "scale_x": 1, "scale_y": 1, "opacity": 1}


def evaluate_transform(layer, frame):
    transform = {**DEFAULT_TRANSFORM, **layer.get("transform", {})}
    return {
        channel: evaluate_track(layer.get("tracks", {}).get(channel, []), frame, value)
        for channel, value in transform.items()
    }


def evaluate_scene(scene, frame):
    return {layer.get("id"): evaluate_transform(layer, frame) for layer in scene.get("layers", [])}
