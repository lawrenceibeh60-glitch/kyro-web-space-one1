"""Evaluate ordered animation layers into a final property pose."""
from engine.animation.animation_blender import blend_pose
from engine.animation.interpolation import evaluate_track


def evaluate_layers(layers, frame, base=None):
    pose = dict(base or {})
    for layer in sorted(layers, key=lambda item: item.get("order", 0)):
        if not layer.get("enabled", True) or not layer.get("tracks"):
            continue
        values = {
            channel: evaluate_track(track, frame, pose.get(channel, 0))
            for channel, track in layer["tracks"].items()
        }
        pose = blend_pose(pose, values, weight=layer.get("weight", 1.0),
                          mode=layer.get("blend_mode", "replace"))
    return pose
