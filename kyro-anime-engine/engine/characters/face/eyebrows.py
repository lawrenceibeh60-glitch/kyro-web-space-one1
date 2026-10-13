"""Eyebrow curve points controlled by expression."""


def eyebrow_points(center, width, *, angle=0, arch=0.15, samples=8):
    if width <= 0 or samples < 2:
        raise ValueError("Invalid eyebrow dimensions")
    x, y = center
    return [(x - width / 2 + width * i / (samples - 1),
             y + angle * (i / (samples - 1) - 0.5) * width
             - arch * width * 4 * (i / (samples - 1) - 0.5) ** 2)
            for i in range(samples)]
