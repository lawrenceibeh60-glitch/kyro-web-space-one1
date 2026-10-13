"""Normalized placement of facial features."""


def layout_features(center, width, height, *, eye_spacing=0.32, eye_y=0.4):
    if width <= 0 or height <= 0 or not 0 < eye_spacing < 1 or not 0 < eye_y < 1:
        raise ValueError("Invalid face dimensions or feature ratios")
    x, y = center
    return {"left_eye": (x - width * eye_spacing / 2, y + height * eye_y),
            "right_eye": (x + width * eye_spacing / 2, y + height * eye_y),
            "nose": (x, y + height * 0.58), "mouth": (x, y + height * 0.76),
            "left_ear": (x - width / 2, y + height * 0.52),
            "right_ear": (x + width / 2, y + height * 0.52)}
