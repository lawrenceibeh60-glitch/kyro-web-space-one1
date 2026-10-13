"""Normalized RGB brightness, contrast, saturation and tint controls."""
import colorsys


def adjust_rgb(color, *, brightness=0, contrast=1, saturation=1, tint=(0, 0, 0)):
    red, green, blue = color[:3]
    values = [max(0, min(1, (channel + brightness - 0.5) * contrast + 0.5 + tint[index]))
              for index, channel in enumerate((red, green, blue))]
    hue, lightness, sat = colorsys.rgb_to_hls(*values)
    values = colorsys.hls_to_rgb(hue, lightness, max(0, min(1, sat * saturation)))
    return (*values, color[3]) if len(color) > 3 else values
