"""Hex, RGB, linear-light, and gamma conversion helpers."""
import re


def hex_to_rgb(value):
    if not isinstance(value, str) or re.fullmatch(r"#[0-9a-fA-F]{6}", value) is None:
        raise ValueError("Expected #RRGGBB")
    return tuple(int(value[index:index + 2], 16) for index in (1, 3, 5))


def rgb_to_hex(rgb):
    if len(rgb) < 3:
        raise ValueError("RGB requires three channels")
    channels = [max(0, min(255, round(float(value)))) for value in rgb[:3]]
    return "#" + "".join(f"{channel:02x}" for channel in channels)


def srgb_to_linear(value):
    value = max(0.0, min(1.0, value))
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def linear_to_srgb(value):
    value = max(0.0, min(1.0, value))
    return 12.92 * value if value <= 0.0031308 else 1.055 * value ** (1 / 2.4) - 0.055


def convert_gamma(rgb, source_gamma=2.2, target_gamma=2.2):
    if source_gamma <= 0 or target_gamma <= 0:
        raise ValueError("Gamma values must be positive")
    return tuple(max(0, value) ** (source_gamma / target_gamma) for value in rgb)
