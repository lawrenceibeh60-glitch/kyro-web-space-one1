"""Blend pose properties with replace, additive, and weighted modes."""


def blend_value(base, overlay, weight=1.0, mode="replace"):
    weight = max(0.0, min(1.0, weight))
    if mode == "replace":
        if isinstance(base, (int, float)) and isinstance(overlay, (int, float)):
            return base + (overlay - base) * weight
        return overlay if weight >= 0.5 else base
    if mode == "add":
        return base + overlay * weight
    if mode == "multiply":
        return base * (1 + (overlay - 1) * weight)
    raise ValueError(f"Unsupported blend mode: {mode}")


def blend_pose(base, overlay, *, weight=1.0, mode="replace"):
    result = dict(base)
    for channel, value in overlay.items():
        result[channel] = blend_value(result.get(channel, 0), value, weight, mode)
    return result
