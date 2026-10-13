"""Hair base/highlight/shadow color derivation."""
from engine.shading.color_management import hex_to_rgb, rgb_to_hex


def shade_color(color, factor):
    if factor < 0:
        raise ValueError("factor must be non-negative")
    return rgb_to_hex(tuple(channel * factor for channel in hex_to_rgb(color)))


def hair_palette(base, highlight=1.25, shadow=0.65):
    return {"shadow": shade_color(base, shadow), "base": base,
            "highlight": shade_color(base, highlight)}
