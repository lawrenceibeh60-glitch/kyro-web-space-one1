"""Camera transform evaluation and world/screen coordinate conversion."""
import math


def world_to_screen(point, camera, *, viewport=(0, 0)):
    x, y = point[0] - camera.get("x", 0), point[1] - camera.get("y", 0)
    zoom_x = camera.get("scale_x", camera.get("zoom", 1))
    zoom_y = camera.get("scale_y", camera.get("zoom", 1))
    angle = math.radians(camera.get("rotation", 0))
    cosine, sine = math.cos(angle), math.sin(angle)
    return (
        viewport[0] + (x * cosine - y * sine) * zoom_x,
        viewport[1] + (x * sine + y * cosine) * zoom_y,
    )


def screen_to_world(point, camera, *, viewport=(0, 0)):
    zoom_x = camera.get("scale_x", camera.get("zoom", 1))
    zoom_y = camera.get("scale_y", camera.get("zoom", 1))
    if zoom_x == 0 or zoom_y == 0:
        raise ValueError("Camera zoom must be non-zero")
    x, y = (point[0] - viewport[0]) / zoom_x, (point[1] - viewport[1]) / zoom_y
    angle = math.radians(-camera.get("rotation", 0))
    cosine, sine = math.cos(angle), math.sin(angle)
    return (x * cosine - y * sine + camera.get("x", 0),
            x * sine + y * cosine + camera.get("y", 0))
