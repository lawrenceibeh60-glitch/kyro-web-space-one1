"""Torso landmark and outline generation."""


def torso_shape(center, width, height, shoulder_ratio=0.8, waist_ratio=0.65):
    if min(width, height) <= 0 or not 0 < shoulder_ratio <= 1 or not 0 < waist_ratio <= 1:
        raise ValueError("Invalid torso dimensions")
    x, y = center
    return [(x - width * shoulder_ratio / 2, y), (x + width * shoulder_ratio / 2, y),
            (x + width / 2, y + height * 0.35), (x + width * waist_ratio / 2, y + height),
            (x - width * waist_ratio / 2, y + height), (x - width / 2, y + height * 0.35)]
