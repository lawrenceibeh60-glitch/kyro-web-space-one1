"""Deterministic camera shake, stable across render order and frame seeking."""
import math


def shake_offset(frame, *, intensity=1.0, speed=1.0, seed=0):
    phase = (frame + seed * 17.17) * speed
    return (math.sin(phase * 12.9898) * intensity,
            math.cos(phase * 7.233) * intensity,
            math.sin(phase * 5.331 + 1.7) * intensity)


def apply_shake(camera, frame, *, intensity=1.0, speed=1.0, seed=0):
    dx, dy, rotation = shake_offset(frame, intensity=intensity, speed=speed, seed=seed)
    return {**camera, "x": camera.get("x", 0) + dx, "y": camera.get("y", 0) + dy,
            "rotation": camera.get("rotation", 0) + rotation}
