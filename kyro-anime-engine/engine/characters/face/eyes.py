"""Anime eye outline and lid geometry."""


def eye_shape(center, width, height, *, openness=1.0):
    if width <= 0 or height <= 0 or not 0 <= openness <= 1:
        raise ValueError("Invalid eye dimensions or openness")
    x, y = center
    half = height * openness / 2
    return {"outline": [(x - width / 2, y), (x, y - half),
                        (x + width / 2, y), (x, y + half)],
            "center": (x, y), "openness": openness}
