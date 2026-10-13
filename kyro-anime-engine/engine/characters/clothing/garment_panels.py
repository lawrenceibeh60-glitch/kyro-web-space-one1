"""Create basic front/back garment panels."""


def rectangular_panel(origin, width, height, *, taper=1.0):
    if width <= 0 or height <= 0 or not 0 < taper <= 1:
        raise ValueError("Invalid panel dimensions")
    x, y = origin
    return [(x - width / 2, y), (x + width / 2, y),
            (x + width * taper / 2, y + height),
            (x - width * taper / 2, y + height)]


def panel_pair(origin, width, height):
    return {"front": rectangular_panel(origin, width, height),
            "back": rectangular_panel(origin, width, height)}
