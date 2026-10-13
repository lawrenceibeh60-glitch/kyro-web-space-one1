"""Mouth curve and phoneme-driven opening."""


def mouth_shape(center, width, openness=0.0, smile=0.0):
    if width <= 0 or openness < 0:
        raise ValueError("Invalid mouth dimensions")
    x, y = center
    return [(x - width / 2, y), (x, y + smile * width / 4 - openness / 2),
            (x + width / 2, y), (x, y + smile * width / 4 + openness / 2)]


def phoneme_mouth(center, width, phoneme):
    opening = {"A": 0.8, "E": 0.45, "I": 0.3, "O": 0.7, "U": 0.4, "M": 0.05}.get(phoneme.upper(), 0.2)
    return mouth_shape(center, width, width * opening)
