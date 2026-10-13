"""Flood-fill a flat pixel buffer using 4-neighbour connectivity."""
from collections import deque


def flood_fill(pixels, width, height, x, y, replacement, *, tolerance=0):
    if width <= 0 or height <= 0 or len(pixels) != width * height:
        raise ValueError("Pixel buffer size must equal width * height")
    if not (0 <= x < width and 0 <= y < height):
        return 0
    target = pixels[y * width + x]
    if target == replacement:
        return 0

    def matches(value):
        if isinstance(target, (tuple, list)) and isinstance(value, (tuple, list)):
            return len(target) == len(value) and sum((a - b) ** 2 for a, b in zip(target, value)) <= tolerance ** 2
        return value == target

    queue, changed = deque([(x, y)]), 0
    while queue:
        px, py = queue.popleft()
        index = py * width + px
        if not matches(pixels[index]):
            continue
        pixels[index] = replacement
        changed += 1
        for nx, ny in ((px - 1, py), (px + 1, py), (px, py - 1), (px, py + 1)):
            if 0 <= nx < width and 0 <= ny < height and matches(pixels[ny * width + nx]):
                queue.append((nx, ny))
    return changed
