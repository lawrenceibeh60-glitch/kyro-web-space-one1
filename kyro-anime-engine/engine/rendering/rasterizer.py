"""Rasterize portable vector draw commands with Pillow when available."""


def rasterize(commands, width, height, *, background="#00000000"):
    try:
        from PIL import Image, ImageColor, ImageDraw
    except ImportError as error:
        raise RuntimeError("Pillow is required for rasterization") from error
    image = Image.new("RGBA", (width, height), _rgba(background, ImageColor))
    draw = ImageDraw.Draw(image, "RGBA")
    ordered = sorted(commands, key=lambda command: getattr(command, "z", 0))
    for command in ordered:
        points = [tuple(point[:2]) for point in getattr(command, "points", [])]
        if not points:
            continue
        opacity = max(0, min(1, getattr(command, "opacity", 1)))
        color = _rgba(getattr(command, "fill", None) or getattr(command, "color", "#111111"), ImageColor, opacity)
        kind = getattr(command, "kind", "line")
        if kind in {"polygon", "fill"} and len(points) >= 3:
            draw.polygon(points, fill=color)
        elif len(points) >= 2:
            draw.line(points, fill=color, width=max(1, round(getattr(command, "width", 1))), joint="curve")
    return image


def _rgba(color, image_color, opacity=1.0):
    if isinstance(color, str) and color.endswith("00") and len(color) == 9:
        return image_color.getcolor(color, "RGBA")
    red, green, blue = image_color.getrgb(color)[:3]
    return red, green, blue, round(255 * opacity)
