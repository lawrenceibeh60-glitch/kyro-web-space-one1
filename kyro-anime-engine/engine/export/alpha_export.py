"""Transparent raster export helpers."""


def export_png(image, path):
    if not hasattr(image, "save"):
        raise TypeError("image must provide a save() method")
    image.save(path, format="PNG")
    return str(path)


def ensure_rgba(image):
    return image.convert("RGBA")
