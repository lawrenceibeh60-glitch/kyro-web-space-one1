"""Quantize diffuse intensity into discrete anime-style shade bands."""


def quantize_intensity(intensity, bands=3):
    if bands < 2:
        raise ValueError("Cel shading requires at least two bands")
    level = max(0.0, min(1.0, intensity))
    return round(level * (bands - 1)) / (bands - 1)


def shade(color, intensity, *, bands=3, ambient=0.15):
    factor = ambient + (1 - ambient) * quantize_intensity(intensity, bands)
    return tuple(max(0.0, min(1.0, channel * factor)) for channel in color[:3])
