"""Palette management, color distance, and nearest-color quantization."""
from engine.shading.color_management import hex_to_rgb


def color_distance(a, b):
    rgb_a = hex_to_rgb(a) if isinstance(a, str) else a
    rgb_b = hex_to_rgb(b) if isinstance(b, str) else b
    return sum((x - y) ** 2 for x, y in zip(rgb_a, rgb_b)) ** 0.5


def nearest_color(color, palette):
    if not palette:
        raise ValueError("Palette must not be empty")
    return min(palette, key=lambda candidate: color_distance(color, candidate))


def unique_palette(colors):
    result = []
    for color in colors:
        if color not in result:
            result.append(color)
    return result
