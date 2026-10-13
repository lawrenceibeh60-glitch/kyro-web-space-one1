"""Point and directional light evaluation."""
import math


def point_light(light, point):
    dx, dy = point[0] - light.get("x", 0), point[1] - light.get("y", 0)
    distance = math.hypot(dx, dy)
    radius = max(1e-9, light.get("radius", 1))
    falloff = max(0.0, 1 - distance / radius) ** 2
    intensity = max(0.0, min(1.0, light.get("intensity", 1)))
    return {"direction": (dx / distance, dy / distance) if distance else (0, -1),
            "intensity": intensity * falloff, "color": light.get("color", "#ffffff")}


def combine_lights(lights, point):
    total = 0.0
    for light in lights:
        total += point_light(light, point)["intensity"]
    return min(1.0, total)
