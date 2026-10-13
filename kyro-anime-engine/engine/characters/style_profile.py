"""Character-generation style settings."""


def create_style(*, line_width=2, palette=None, head_ratio=1.0, detail=0.5):
    if line_width <= 0 or head_ratio <= 0 or not 0 <= detail <= 1:
        raise ValueError("Invalid style dimensions or detail (0..1)")
    return {"line_width": line_width, "palette": list(palette or []),
            "head_ratio": head_ratio, "detail": detail}
